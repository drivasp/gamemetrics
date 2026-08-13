"""Regiones comerciales, monedas e impuestos por país (Fase 3)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryLocale:
    country_code: str
    name: str
    pricing_region: str  # US | EU | LATAM (fact_price_catalog)
    currency: str
    tax_rate_pct: float
    tax_name: str
    flag: str = ""


# Tasas reales aproximadas para bienes digitales (demo académica).
# US: muchos estados no gravan software digital descargable → 0% en demo.
COUNTRIES: dict[str, CountryLocale] = {
    "US": CountryLocale("US", "Estados Unidos", "US", "USD", 0.0, "Sales tax (digital exempt)", "🇺🇸"),
    "CA": CountryLocale("CA", "Canadá", "US", "USD", 5.0, "GST", "🇨🇦"),
    "MX": CountryLocale("MX", "México", "LATAM", "USD", 16.0, "IVA", "🇲🇽"),
    "EC": CountryLocale("EC", "Ecuador", "LATAM", "USD", 15.0, "IVA", "🇪🇨"),
    "CO": CountryLocale("CO", "Colombia", "LATAM", "USD", 19.0, "IVA", "🇨🇴"),
    "AR": CountryLocale("AR", "Argentina", "LATAM", "USD", 21.0, "IVA", "🇦🇷"),
    "CL": CountryLocale("CL", "Chile", "LATAM", "USD", 19.0, "IVA", "🇨🇱"),
    "PE": CountryLocale("PE", "Perú", "LATAM", "USD", 18.0, "IGV", "🇵🇪"),
    "BR": CountryLocale("BR", "Brasil", "LATAM", "USD", 0.0, "ISS (demo 0%)", "🇧🇷"),
    "ES": CountryLocale("ES", "España", "EU", "EUR", 21.0, "IVA", "🇪🇸"),
    "FR": CountryLocale("FR", "Francia", "EU", "EUR", 20.0, "TVA", "🇫🇷"),
    "DE": CountryLocale("DE", "Alemania", "EU", "EUR", 19.0, "MwSt", "🇩🇪"),
    "IT": CountryLocale("IT", "Italia", "EU", "EUR", 22.0, "IVA", "🇮🇹"),
    "GB": CountryLocale("GB", "Reino Unido", "EU", "EUR", 20.0, "VAT", "🇬🇧"),
}

DEFAULT_COUNTRY = "US"


def normalize_country(code: str | None) -> str:
    c = (code or DEFAULT_COUNTRY).strip().upper()
    if c in COUNTRIES:
        return c
    return DEFAULT_COUNTRY


def get_locale(country_code: str | None) -> CountryLocale:
    return COUNTRIES[normalize_country(country_code)]


def compute_tax(taxable_amount: float, country_code: str | None) -> dict:
    loc = get_locale(country_code)
    taxable = round(max(0.0, float(taxable_amount)), 2)
    tax_amount = round(taxable * (loc.tax_rate_pct / 100.0), 2)
    total = round(taxable + tax_amount, 2)
    return {
        "country_code": loc.country_code,
        "country_name": loc.name,
        "pricing_region": loc.pricing_region,
        "currency": loc.currency,
        "tax_name": loc.tax_name,
        "tax_rate_pct": loc.tax_rate_pct,
        "taxable_amount": taxable,
        "tax_amount": tax_amount,
        "total_with_tax": total,
    }


def list_countries() -> list[dict]:
    return [
        {
            "country_code": c.country_code,
            "name": c.name,
            "pricing_region": c.pricing_region,
            "currency": c.currency,
            "tax_rate_pct": c.tax_rate_pct,
            "tax_name": c.tax_name,
            "flag": c.flag,
        }
        for c in COUNTRIES.values()
    ]
