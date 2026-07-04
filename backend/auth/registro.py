import time

from fastapi import APIRouter, HTTPException

from auth.modelos_auth import RegisterDTO, AuthResponseDTO, UserDTO
from auth.cliente_jwt import hash_password, create_token, new_id
from shared.cliente_pinot import pinot_query, PinotUnavailableError
from shared.kafka_producer import kafka_send

router = APIRouter()


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


@router.post("/register", response_model=AuthResponseDTO)
async def register(body: RegisterDTO):
    try:
        existing = await pinot_query(
            f"SELECT user_id FROM fact_users WHERE email = '{_esc(body.email)}' AND deleted = FALSE LIMIT 1",
            raise_on_error=True,
        )
    except PinotUnavailableError:
        raise HTTPException(
            503,
            "El servicio de cuentas no está disponible temporalmente. Intenta de nuevo en unos segundos.",
        )
    if existing:
        raise HTTPException(400, "Este email ya está en uso")

    user_id = new_id()
    password_hash = hash_password(body.password)
    now_ms = int(time.time() * 1000)

    await kafka_send("fact_users", user_id, {
        "user_id": user_id,
        "email": body.email,
        "password_hash": password_hash,
        "display_name": body.display_name or "",
        "bio": "",
        "avatar": "",
        "deleted": False,
        "created_at": now_ms,
    })

    token = create_token(user_id, body.email)
    return AuthResponseDTO(
        token=token,
        user=UserDTO(
            id=user_id,
            email=body.email,
            display_name=body.display_name or None,
            bio=None,
            avatar=None,
        ),
    )
