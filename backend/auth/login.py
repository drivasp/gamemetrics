from fastapi import APIRouter, HTTPException, Request

from auth.modelos_auth import LoginDTO, AuthResponseDTO, UserDTO
from auth.cliente_jwt import verify_password, create_token, new_id
from auth.roles import get_user_role
from auth import user_cache
from shared.cliente_pinot import pinot_query, PinotUnavailableError
from shared.kafka_producer import kafka_send
import hashlib
import time

router = APIRouter()


def _esc(s: str) -> str:
    return s.replace(chr(39), chr(39)*2).replace(chr(92), chr(92)*2)


@router.post("/login", response_model=AuthResponseDTO)
async def login(body: LoginDTO, request: Request):
    email_q = body.email.strip().lower()
    rows: list = []
    pinot_down = False
    try:
        # Upsert PK is user_id, so the same email can have multiple rows after
        # register races / Pinot lag. Try all non-deleted matches (newest first).
        rows = await pinot_query(
            f"SELECT user_id, email, password_hash, display_name, bio, avatar, created_at "
            f"FROM fact_users WHERE lower(email) = '{_esc(email_q)}' AND deleted = FALSE "
            f"ORDER BY created_at DESC LIMIT 20",
            raise_on_error=True,
        )
    except PinotUnavailableError:
        pinot_down = True
        rows = []

    # Merge cache (cubre lag de Pinot y registro recién hecho en este proceso).
    by_id: dict[str, tuple] = {}
    for row in rows or []:
        by_id[str(row[0])] = tuple(row[:7])
    for cached in user_cache.list_by_email(email_q):
        by_id[str(cached["user_id"])] = (
            cached["user_id"],
            cached["email"],
            cached["password_hash"],
            cached.get("display_name") or "",
            cached.get("bio") or "",
            cached.get("avatar") or "",
            cached.get("created_at") or 0,
        )

    candidates = sorted(by_id.values(), key=lambda r: int(r[6] or 0), reverse=True)
    if not candidates:
        if pinot_down:
            raise HTTPException(
                503,
                "El servicio de cuentas no está disponible temporalmente. Intenta de nuevo en unos segundos.",
            )
        raise HTTPException(400, "Email o contraseña incorrectos")

    matched = None
    for row in candidates:
        user_id, email, password_hash, display_name, bio, avatar = row[:6]
        if password_hash and verify_password(body.password, password_hash):
            matched = (user_id, email, display_name, bio, avatar)
            break

    if matched is None:
        raise HTTPException(400, "Email o contraseña incorrectos")

    user_id, email, display_name, bio, avatar = matched

    try:
        now_ms = int(time.time() * 1000)
        sanctions = await pinot_query(
            f"SELECT sanction_type, reason, expires_at FROM fact_user_sanctions "
            f"WHERE user_id = '{_esc(user_id)}' AND deleted = false LIMIT 10"
        )
        for stype, reason, expires in sanctions:
            exp = int(expires or 0)
            if exp == 0 or exp > now_ms:
                raise HTTPException(
                    403,
                    f"Cuenta sancionada ({stype}): {reason or 'Contacta soporte'}",
                )
    except HTTPException:
        raise
    except Exception:
        pass

    role = await get_user_role(user_id)
    token = create_token(user_id, email, role=role)

    session_id = new_id()
    now_ms = int(time.time() * 1000)
    expires_ms = now_ms + (7 * 24 * 60 * 60 * 1000)
    client = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client.encode()).hexdigest()[:16]
    await kafka_send("fact_user_sessions", session_id, {
        "session_id": session_id,
        "user_id": user_id,
        "device_info": request.headers.get("user-agent", "web")[:200],
        "ip_hash": ip_hash,
        "last_seen_at": now_ms,
        "expires_at": expires_ms,
        "created_at": now_ms,
        "deleted": False,
    })

    return AuthResponseDTO(
        token=token,
        user=UserDTO(
            id=user_id,
            email=email,
            display_name=display_name or None,
            bio=bio or None,
            avatar=avatar or None,
            role=role,
        ),
    )
