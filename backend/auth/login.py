from fastapi import APIRouter, HTTPException, Request

from auth.modelos_auth import LoginDTO, AuthResponseDTO, UserDTO
from auth.cliente_jwt import verify_password, create_token, new_id
from shared.cliente_pinot import pinot_query, PinotUnavailableError
from shared.kafka_producer import kafka_send
import hashlib
import time

router = APIRouter()


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


@router.post("/login", response_model=AuthResponseDTO)
async def login(body: LoginDTO, request: Request):
    try:
        rows = await pinot_query(
            f"SELECT user_id, email, password_hash, display_name, bio, avatar "
            f"FROM fact_users WHERE email = '{_esc(body.email)}' AND deleted = FALSE LIMIT 1",
            raise_on_error=True,
        )
    except PinotUnavailableError:
        raise HTTPException(
            503,
            "El servicio de cuentas no está disponible temporalmente. Intenta de nuevo en unos segundos.",
        )
    if not rows:
        raise HTTPException(400, "Email o contraseña incorrectos")

    user_id, email, password_hash, display_name, bio, avatar = rows[0]

    if not verify_password(body.password, password_hash):
        raise HTTPException(400, "Email o contraseña incorrectos")

    # Moderación: sanciones activas
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

    token = create_token(user_id, email)

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
        ),
    )
