"""Resolve pricing region / country for storefront requests."""
from __future__ import annotations

from regional.router import get_user_country
from shared.auth_deps import require_token
from shared.region_tax import get_locale


async def resolve_request_locale(
    authorization: str | None = None,
    country: str | None = None,
) -> dict:
    """Logged-in users ALWAYS use account country (anti tax evasion).

    Guests may pass ?country= for browsing only; checkout requires account.
    """
    if authorization:
        try:
            _, user_id = require_token(authorization)
            code = await get_user_country(user_id)
            loc = get_locale(code)
            return {
                "country_code": loc.country_code,
                "pricing_region": loc.pricing_region,
                "currency": loc.currency,
                "tax_rate_pct": loc.tax_rate_pct,
                "tax_name": loc.tax_name,
            }
        except Exception:
            pass
    # Invitados: solo para ver catálogo (no aplica a pago)
    if country and country.strip():
        loc = get_locale(country)
        return {
            "country_code": loc.country_code,
            "pricing_region": loc.pricing_region,
            "currency": loc.currency,
            "tax_rate_pct": loc.tax_rate_pct,
            "tax_name": loc.tax_name,
        }
    loc = get_locale("US")
    return {
        "country_code": loc.country_code,
        "pricing_region": loc.pricing_region,
        "currency": loc.currency,
        "tax_rate_pct": loc.tax_rate_pct,
        "tax_name": loc.tax_name,
    }
