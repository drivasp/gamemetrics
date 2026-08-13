"""Preferencia de país / región del usuario (Fase 3).

El país de residencia se fija en el registro (estilo Steam) y NO se puede
cambiar libremente desde la tienda para evadir impuestos.
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.region_tax import DEFAULT_COUNTRY, get_locale, list_countries, normalize_country

router = APIRouter(prefix="/locale", tags=["locale"])

# Cache en memoria para mitigar lag de Pinot tras registro
_LOCALE_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL_S = 300.0


class LocaleUpdateDTO(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)


def cache_set_user_country(user_id: str, country_code: str) -> None:
    _LOCALE_CACHE[user_id] = (normalize_country(country_code), time.time())


def _cache_get(user_id: str) -> str | None:
    hit = _LOCALE_CACHE.get(user_id)
    if not hit:
        return None
    code, ts = hit
    if time.time() - ts > _CACHE_TTL_S:
        _LOCALE_CACHE.pop(user_id, None)
        return None
    return code


async def get_user_country(user_id: str) -> str:
    cached = _cache_get(user_id)
    if cached:
        return cached
    rows = await pinot_query(
        f"SELECT country_code FROM fact_user_locale "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if not rows or not rows[0][0]:
        return DEFAULT_COUNTRY
    code = normalize_country(str(rows[0][0]))
    cache_set_user_country(user_id, code)
    return code


async def get_user_locale_info(user_id: str) -> dict:
    country = await get_user_country(user_id)
    loc = get_locale(country)
    return {
        "country_code": loc.country_code,
        "country_name": loc.name,
        "pricing_region": loc.pricing_region,
        "currency": loc.currency,
        "tax_rate_pct": loc.tax_rate_pct,
        "tax_name": loc.tax_name,
        "flag": loc.flag,
        "locked": True,
        "change_policy": (
            "El país de residencia se define al crear la cuenta y no se puede "
            "cambiar libremente (precios e impuestos fiscales)."
        ),
    }


@router.get("/countries")
async def countries():
    return {"items": list_countries()}


@router.get("/me")
async def my_locale(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    return await get_user_locale_info(user_id)


@router.put("/me")
async def set_locale(
    body: LocaleUpdateDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    """Bloqueado a propósito: evitar evasión de impuestos cambiando de país."""
    require_token(authorization)
    # Validar body para no romper clientes, pero siempre rechazar el cambio.
    _ = normalize_country(body.country_code)
    raise HTTPException(
        403,
        detail=(
            "No puedes cambiar el país de residencia desde la tienda. "
            "Se asigna al registrarte (como en Steam) para calcular precios e impuestos. "
            "Si te mudaste de país, contacta soporte con verificación."
        ),
    )
