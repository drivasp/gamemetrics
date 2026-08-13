import time

from fastapi import APIRouter, HTTPException

from auth.modelos_auth import RegisterDTO, AuthResponseDTO, UserDTO, BootstrapAdminDTO
from auth.cliente_jwt import hash_password, create_token, new_id
from auth.roles import ROLE_BOOTSTRAP_SECRET, get_user_role, set_user_role
from auth import user_cache
from regional.router import cache_set_user_country
from shared.cliente_pinot import pinot_query, PinotUnavailableError
from shared.kafka_producer import kafka_send
from shared.region_tax import get_locale, normalize_country, list_countries

router = APIRouter()


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


async def _create_user(
    *,
    email: str,
    password: str,
    display_name: str | None,
    country_code: str,
    role: str,
) -> AuthResponseDTO:
    country = normalize_country(country_code)
    if country not in {c["country_code"] for c in list_countries()}:
        raise HTTPException(400, "País de residencia no soportado")
    loc = get_locale(country)

    existing = []
    pinot_down = False
    try:
        existing = await pinot_query(
            f"SELECT user_id FROM fact_users WHERE lower(email) = '{_esc(email)}' AND deleted = FALSE LIMIT 1",
            raise_on_error=True,
        )
    except PinotUnavailableError:
        pinot_down = True
        existing = []

    if existing or user_cache.get_by_email(email):
        raise HTTPException(400, "Este email ya está en uso")

    # Si Pinot está caído no bloqueamos el alta: Kafka + cache permiten login inmediato.
    if pinot_down:
        print("[auth] Pinot down en register — usando cache + Kafka")

    user_id = new_id()
    password_hash = hash_password(password)
    now_ms = int(time.time() * 1000)

    await kafka_send("fact_users", user_id, {
        "user_id": user_id,
        "email": email,
        "password_hash": password_hash,
        "display_name": display_name or "",
        "bio": "",
        "avatar": "",
        "deleted": False,
        "created_at": now_ms,
    })
    user_cache.cache_user(
        user_id=user_id,
        email=email,
        password_hash=password_hash,
        display_name=display_name or "",
        created_at=now_ms,
    )

    cache_set_user_country(user_id, loc.country_code)
    await kafka_send("fact_user_locale", user_id, {
        "user_id": user_id,
        "country_code": loc.country_code,
        "pricing_region": loc.pricing_region,
        "currency": loc.currency,
        "updated_at": now_ms,
        "deleted": False,
    })

    role = await set_user_role(user_id, role)
    token = create_token(user_id, email, role=role)
    return AuthResponseDTO(
        token=token,
        user=UserDTO(
            id=user_id,
            email=email,
            display_name=display_name or None,
            bio=None,
            avatar=None,
            country_code=loc.country_code,
            role=role,
        ),
    )


@router.post("/register", response_model=AuthResponseDTO)
async def register(body: RegisterDTO):
    email = body.email.strip().lower()
    return await _create_user(
        email=email,
        password=body.password,
        display_name=body.display_name,
        country_code=body.country_code,
        role="player",
    )


@router.post("/bootstrap-admin", response_model=AuthResponseDTO)
async def bootstrap_admin(body: BootstrapAdminDTO):
    """Crea (o promueve) un admin. Protegido por ROLE_BOOTSTRAP_SECRET."""
    if not ROLE_BOOTSTRAP_SECRET or body.secret != ROLE_BOOTSTRAP_SECRET:
        raise HTTPException(403, "Secret de bootstrap inválido")

    email = body.email.strip().lower()
    rows = await pinot_query(
        f"SELECT user_id, password_hash, display_name, bio, avatar "
        f"FROM fact_users WHERE lower(email) = '{_esc(email)}' AND deleted = FALSE LIMIT 1"
    )
    if rows:
        user_id = rows[0][0]
        role = await set_user_role(user_id, "admin")
        token = create_token(user_id, email, role=role)
        return AuthResponseDTO(
            token=token,
            user=UserDTO(
                id=user_id,
                email=email,
                display_name=rows[0][2] or body.display_name or None,
                bio=rows[0][3] or None,
                avatar=rows[0][4] or None,
                role=role,
            ),
        )

    return await _create_user(
        email=email,
        password=body.password,
        display_name=body.display_name or "Admin",
        country_code=body.country_code,
        role="admin",
    )
