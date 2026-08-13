"""
Steam Direct Fee — tarifa de publicación (estilo Valve).

Fuente oficial Valve:
https://partner.steamgames.com/doc/gettingstarted/appfee
- Fee: $100 USD (o equivalente) por app
- No reembolsable
- Recuperable (recoup) tras $1,000 Adjusted Gross Revenue
- No se puede pagar con Steam Wallet
- VAT/GST pueden aplicarse según país (revisar con asesor fiscal)

GameMetrics:
- PUBLICATION_FEE_USD (default 100; 0 desactiva)
- PUBLICATION_FEE_RECOUP_USD (default 1000)
- Asientos ledger: direct_fee (débitos al partner) / direct_fee_recoup (crédito)
"""
from __future__ import annotations

import os
import time
from typing import Any

from checkout.partner_ledger import _cache_put, list_partner_ledger
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

PUBLICATION_FEE_USD = float(os.getenv("PUBLICATION_FEE_USD", "100"))
PUBLICATION_FEE_RECOUP_USD = float(os.getenv("PUBLICATION_FEE_RECOUP_USD", "1000"))


def direct_fee_ledger_id(partner_id: str, product_id: str) -> str:
    return f"dfee_{partner_id[:8]}_{product_id}"[:64]


def direct_fee_recoup_ledger_id(partner_id: str, product_id: str) -> str:
    return f"dfeer_{partner_id[:8]}_{product_id}"[:64]


async def _entry_exists(entry_id: str) -> bool:
    from checkout.partner_ledger import _LEDGER_CACHE

    if entry_id in _LEDGER_CACHE and not _LEDGER_CACHE[entry_id].get("deleted"):
        return True
    rows = await pinot_query(
        f"SELECT ledger_entry_id FROM fact_partner_ledger "
        f"WHERE ledger_entry_id = '{esc(entry_id)}' AND deleted = false LIMIT 1"
    )
    return bool(rows)


async def charge_publication_fee(
    *,
    partner_id: str,
    product_id: str,
    game_name: str,
    charged_by: str,
    amount: float | None = None,
) -> dict[str, Any] | None:
    """
    Cobra la tarifa de publicación contra el saldo futuro del partner
    (asiento negativo en publisher_net). Idempotente por partner+product.
    Si PUBLICATION_FEE_USD <= 0, no hace nada.
    """
    fee = float(amount if amount is not None else PUBLICATION_FEE_USD)
    if fee <= 0:
        return None

    entry_id = direct_fee_ledger_id(partner_id, product_id)
    if await _entry_exists(entry_id):
        from checkout.partner_ledger import _LEDGER_CACHE

        return _LEDGER_CACHE.get(entry_id) or {"ledger_entry_id": entry_id, "status": "already_charged"}

    now = int(time.time() * 1000)
    entry = {
        "ledger_entry_id": entry_id,
        "partner_id": partner_id,
        "order_id": "",
        "product_id": product_id,
        "game_name": game_name or product_id,
        "buyer_user_id": charged_by,
        "entry_type": "direct_fee",
        "currency": "USD",
        "status": "available",
        "related_entry_id": "",
        "quantity": 0,
        "gross_amount": 0.0,
        "platform_fee_amount": fee,  # ingreso plataforma (tarifa)
        "publisher_net_amount": -fee,  # reduce saldo publisher hasta recoup
        "publisher_share_pct": 0.0,
        "platform_take_rate_pct": 100.0,
        "created_at": now,
        "deleted": False,
    }
    _cache_put(entry)
    await kafka_send("fact_partner_ledger", entry_id, entry)
    return entry


async def maybe_recoup_publication_fee(
    *,
    partner_id: str,
    product_id: str,
    game_name: str = "",
) -> dict[str, Any] | None:
    """
    Si AGR del producto (ventas - refunds - chargebacks) ≥ umbral y hay fee cobrado
    sin recoup, acredita el fee de vuelta al publisher (línea separada, estilo Steam).
    """
    if PUBLICATION_FEE_USD <= 0:
        return None

    fee_id = direct_fee_ledger_id(partner_id, product_id)
    recoup_id = direct_fee_recoup_ledger_id(partner_id, product_id)
    if not await _entry_exists(fee_id):
        return None
    if await _entry_exists(recoup_id):
        return None

    entries = await list_partner_ledger(partner_id, limit=500)
    agr = 0.0
    fee_amt = PUBLICATION_FEE_USD
    for e in entries:
        if e.get("product_id") != product_id:
            continue
        et = e.get("entry_type")
        if et in ("sale", "refund", "chargeback"):
            agr += float(e.get("gross_amount") or 0)
        if et == "direct_fee" and e.get("ledger_entry_id") == fee_id:
            fee_amt = abs(float(e.get("platform_fee_amount") or PUBLICATION_FEE_USD))

    if agr + 0.001 < PUBLICATION_FEE_RECOUP_USD:
        return None

    now = int(time.time() * 1000)
    entry = {
        "ledger_entry_id": recoup_id,
        "partner_id": partner_id,
        "order_id": "",
        "product_id": product_id,
        "game_name": game_name or product_id,
        "buyer_user_id": "system",
        "entry_type": "direct_fee_recoup",
        "currency": "USD",
        "status": "available",
        "related_entry_id": fee_id,
        "quantity": 0,
        "gross_amount": 0.0,
        "platform_fee_amount": -fee_amt,  # plataforma devuelve la tarifa
        "publisher_net_amount": fee_amt,
        "publisher_share_pct": 0.0,
        "platform_take_rate_pct": 0.0,
        "created_at": now,
        "deleted": False,
    }
    _cache_put(entry)
    await kafka_send("fact_partner_ledger", recoup_id, entry)
    return entry


def publication_fee_policy() -> dict[str, Any]:
    return {
        "fee_usd": PUBLICATION_FEE_USD,
        "recoup_threshold_usd": PUBLICATION_FEE_RECOUP_USD,
        "enabled": PUBLICATION_FEE_USD > 0,
        "steam_reference": {
            "fee_usd": 100,
            "recoup_agr_usd": 1000,
            "source": "https://partner.steamgames.com/doc/gettingstarted/appfee",
            "source_type": "official",
        },
        "note": (
            "La tarifa GameMetrics es configurable. Decisión empresarial pendiente: "
            "monto exacto, si aplica VAT/GST, y método de cobro (tarjeta vs saldo)."
        ),
    }
