"""
Chargebacks — disputas de pago (arquitectura lista; integración PSP pendiente).

Un chargeback ocurre cuando el titular de la tarjeta disputa el cargo ante el banco.
En plataformas digitales suele:
- revertir el ingreso al publisher (como un refund forzado),
- generar fees del procesador (Stripe ~$15 — VERIFICAR con contrato PSP; no hardcodear como ingreso),
- afectar el riesgo / hold de payouts.

GameMetrics registra el asiento inverso idempotente. El fee del PSP y la
comunicación con Stripe Disputes requieren STRIPE_WEBHOOK_SECRET y decisión operativa.
"""
from __future__ import annotations

import time
from typing import Any

from checkout.partner_ledger import (
    _LEDGER_CACHE,
    _cache_put,
    resolve_partner_for_product,
    sale_ledger_id,
    split_revenue,
)
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send


def chargeback_ledger_id(payment_id: str, product_id: str = "") -> str:
    raw = f"cb_{payment_id}_{product_id}" if product_id else f"cb_{payment_id}"
    return raw[:64]


async def record_chargeback_ledger(
    *,
    payment_id: str,
    order_id: str,
    buyer_user_id: str,
    product_id: str,
    game_name: str,
    amount: float,
    currency: str = "USD",
    reason: str = "payment_dispute",
    created_by: str = "system",
) -> dict[str, Any] | None:
    """
    Asiento inverso tipo chargeback. Idempotente por payment_id + product_id.
    Usa el split de la venta original si existe.
    """
    entry_id = chargeback_ledger_id(payment_id, product_id)
    if entry_id in _LEDGER_CACHE and not _LEDGER_CACHE[entry_id].get("deleted"):
        return _LEDGER_CACHE[entry_id]

    rows = await pinot_query(
        f"SELECT ledger_entry_id FROM fact_partner_ledger "
        f"WHERE ledger_entry_id = '{esc(entry_id)}' AND deleted = false LIMIT 1"
    )
    if rows:
        return {"ledger_entry_id": entry_id, "status": "already_recorded"}

    sale_id = sale_ledger_id(order_id, product_id)
    original = _LEDGER_CACHE.get(sale_id)
    if not original:
        found = await pinot_query(
            f"SELECT ledger_entry_id, partner_id, game_name, currency, quantity, "
            f"gross_amount, platform_fee_amount, publisher_net_amount, "
            f"publisher_share_pct, platform_take_rate_pct "
            f"FROM fact_partner_ledger "
            f"WHERE ledger_entry_id = '{esc(sale_id)}' AND deleted = false LIMIT 1"
        )
        if found:
            r = found[0]
            original = {
                "partner_id": r[1],
                "game_name": r[2],
                "currency": r[3],
                "quantity": int(r[4] or 1),
                "gross_amount": float(r[5] or 0),
                "platform_fee_amount": float(r[6] or 0),
                "publisher_net_amount": float(r[7] or 0),
                "publisher_share_pct": float(r[8] or 70),
                "platform_take_rate_pct": float(r[9] or 30),
            }

    if original:
        partner_id = original["partner_id"]
        g = -abs(float(original["gross_amount"]))
        fee = -abs(float(original["platform_fee_amount"]))
        net = -abs(float(original["publisher_net_amount"]))
        share = float(original["publisher_share_pct"])
        take = float(original["platform_take_rate_pct"])
        qty = -abs(int(original.get("quantity") or 1))
        cur = original.get("currency") or currency
        gname = original.get("game_name") or game_name
        related = sale_id
    else:
        attr = await resolve_partner_for_product(product_id)
        if not attr:
            return None
        from checkout.partner_ledger import _money

        g0, fee0, net0, take = split_revenue(abs(float(amount or 0)), attr.publisher_share_pct)
        partner_id = attr.partner_id
        g, fee, net = -g0, -fee0, -net0
        share = attr.publisher_share_pct
        qty = -1
        cur = currency
        gname = game_name or attr.game_name
        related = ""

    now = int(time.time() * 1000)
    entry = {
        "ledger_entry_id": entry_id,
        "partner_id": partner_id,
        "order_id": order_id,
        "product_id": product_id,
        "game_name": gname,
        "buyer_user_id": buyer_user_id,
        "entry_type": "chargeback",
        "currency": str(cur).upper(),
        "status": "available",
        "related_entry_id": related,
        "quantity": qty,
        "gross_amount": g,
        "platform_fee_amount": fee,
        "publisher_net_amount": net,
        "publisher_share_pct": share,
        "platform_take_rate_pct": take,
        "created_at": now,
        "deleted": False,
        "meta_reason": reason,
        "meta_created_by": created_by,
    }
    # Solo campos del schema Pinot van a Kafka; meta se queda en cache local
    kafka_row = {k: v for k, v in entry.items() if not k.startswith("meta_")}
    _cache_put(kafka_row)
    await kafka_send("fact_partner_ledger", entry_id, kafka_row)
    return entry
