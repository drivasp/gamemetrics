"""
Tax Engine configurable — tasas por jurisdicción.

Las tasas en tax_rules.json son CONFIGURACIÓN DEMO / planificación.
NO constituyen asesoramiento fiscal. Jurisdicciones reales requieren
revisión legal/contable (OPEN_DEPENDENCIES D05).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_RULES_PATH = Path(__file__).resolve().parent / "tax_rules.json"
_AUDIT: list[dict[str, Any]] = []


def load_rules() -> dict[str, Any]:
    if _RULES_PATH.exists():
        return json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    # Fallback mirrors shared.region_tax demo
    return {
        "default_country": "US",
        "jurisdictions": {
            "US": {"tax_name": "Sales tax", "rate_pct": 0.0, "tax_included_in_price": False, "currency": "USD", "pricing_region": "US"},
            "MX": {"tax_name": "IVA", "rate_pct": 16.0, "tax_included_in_price": False, "currency": "USD", "pricing_region": "LATAM"},
            "ES": {"tax_name": "IVA", "rate_pct": 21.0, "tax_included_in_price": True, "currency": "EUR", "pricing_region": "EU"},
        },
    }


def get_jurisdiction(country_code: str) -> dict[str, Any]:
    rules = load_rules()
    code = (country_code or rules.get("default_country") or "US").upper()
    j = rules.get("jurisdictions", {}).get(code)
    if not j:
        j = rules.get("jurisdictions", {}).get(rules.get("default_country", "US"), {
            "tax_name": "Tax",
            "rate_pct": 0.0,
            "tax_included_in_price": False,
            "currency": "USD",
            "pricing_region": "US",
            "status": "pending_legal_config",
        })
        return {**j, "country_code": code, "status": "pending_legal_config"}
    return {"country_code": code, **j}


def calculate_tax(
    amount: float,
    country_code: str,
    *,
    order_id: str = "",
    actor_id: str = "system",
) -> dict[str, Any]:
    j = get_jurisdiction(country_code)
    rate = float(j.get("rate_pct") or 0)
    included = bool(j.get("tax_included_in_price"))
    amt = round(max(0.0, float(amount)), 2)

    if included and rate > 0:
        # amount is gross including tax
        net = round(amt / (1 + rate / 100.0), 2)
        tax = round(amt - net, 2)
        taxable = net
        total = amt
    else:
        taxable = amt
        tax = round(taxable * (rate / 100.0), 2)
        total = round(taxable + tax, 2)

    result = {
        "country_code": j["country_code"],
        "tax_name": j.get("tax_name") or "Tax",
        "tax_rate_pct": rate,
        "tax_included_in_price": included,
        "currency": j.get("currency") or "USD",
        "pricing_region": j.get("pricing_region") or "US",
        "taxable_amount": taxable,
        "tax_amount": tax,
        "total_with_tax": total,
        "status": j.get("status") or "configured_demo",
        "legal_note": "Configurable demo rates — verify with tax counsel before production.",
    }
    _AUDIT.insert(0, {
        "audit_id": f"tax_{int(time.time()*1000)}_{order_id[:8]}",
        "actor_id": actor_id,
        "order_id": order_id,
        "action": "calculate_tax",
        "result": result,
        "created_at": int(time.time() * 1000),
    })
    del _AUDIT[500:]
    return result


def list_tax_audit(limit: int = 50) -> list[dict[str, Any]]:
    return _AUDIT[:limit]
