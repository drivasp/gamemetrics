"""
Estado financiero tipo Steam monthly report (conceptual).

Produce un desglose:
  gross → taxes (si se pasan) → refunds → chargebacks → adjusted → platform fee → publisher net
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from checkout.partner_ledger import list_partner_ledger
from checkout.partner_payouts import list_partner_payouts, partner_balance


def _money(v: float) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


async def build_partner_financial_statement(
    partner_id: str,
    *,
    tax_collected: float | None = None,
) -> dict[str, Any]:
    """
    tax_collected: opcional. Impuestos NO se reparten; se muestran informativos.
    Valve no publica el layout exacto del CSV mensual; este es el equivalente GameMetrics.
    """
    entries = await list_partner_ledger(partner_id, limit=500)
    payouts = await list_partner_payouts(partner_id, limit=100)
    bal = await partner_balance(partner_id)

    sales_gross = 0.0
    refunds_gross = 0.0
    chargebacks_gross = 0.0
    platform_fee = 0.0
    publisher_net = 0.0
    direct_fees = 0.0
    direct_recoups = 0.0
    units = 0
    sale_count = 0
    refund_count = 0
    chargeback_count = 0

    for e in entries:
        et = e.get("entry_type")
        g = float(e.get("gross_amount") or 0)
        fee = float(e.get("platform_fee_amount") or 0)
        net = float(e.get("publisher_net_amount") or 0)
        if et == "sale":
            sales_gross += g
            platform_fee += fee
            publisher_net += net
            units += int(e.get("quantity") or 0)
            sale_count += 1
        elif et == "refund":
            refunds_gross += abs(g)
            platform_fee += fee  # fee ya negativo
            publisher_net += net
            refund_count += 1
        elif et == "chargeback":
            chargebacks_gross += abs(g)
            platform_fee += fee
            publisher_net += net
            chargeback_count += 1
        elif et == "direct_fee":
            direct_fees += abs(fee)
            platform_fee += fee
            publisher_net += net
        elif et == "direct_fee_recoup":
            direct_recoups += abs(net)
            platform_fee += fee
            publisher_net += net
        elif et == "payout":
            continue

    adjusted = _money(sales_gross - refunds_gross - chargebacks_gross)
    taxes = _money(tax_collected) if tax_collected is not None else None

    return {
        "partner_id": partner_id,
        "units_sold": max(0, units),
        "sales_count": sale_count,
        "gross_revenue": _money(sales_gross),
        "taxes_collected_info": taxes,
        "taxes_note": (
            "Los impuestos al consumidor no forman parte del revenue share. "
            "Revisar con asesor fiscal/legal obligaciones de recaudación (VAT/GST/sales tax)."
        ),
        "refunds": _money(refunds_gross),
        "refund_count": refund_count,
        "chargebacks": _money(chargebacks_gross),
        "chargeback_count": chargeback_count,
        "adjusted_gross_revenue": adjusted,
        "platform_commission": _money(platform_fee),
        "publication_fees": _money(direct_fees),
        "publication_fee_recoups": _money(direct_recoups),
        "publisher_earnings": _money(publisher_net),
        "balance_pending": bal.get("balance_pending"),
        "balance_available": bal.get("balance_available"),
        "balance_paid_out": bal.get("balance_paid_out"),
        "next_payout_eligible": bal.get("balance_available"),
        "payout_min_usd": bal.get("payout_min_usd"),
        "hold_days": bal.get("hold_days"),
        "recent_payouts": payouts[:10],
        "formula": (
            "AGR ≈ sales_gross − refunds − chargebacks; "
            "publisher_earnings = sum(publisher_net) incl. fees/recoups; "
            "available = earnings_out_of_hold − paid_out"
        ),
    }
