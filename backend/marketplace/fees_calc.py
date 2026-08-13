"""Cálculo puro de fees de marketplace (sin I/O ni Kafka)."""
from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP

PLATFORM_FEE_PCT = float(os.getenv("MARKETPLACE_PLATFORM_FEE_PCT", "5"))
GAME_FEE_PCT = float(os.getenv("MARKETPLACE_GAME_FEE_PCT", "10"))


def _money(v: float) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def fee_breakdown(price: float) -> dict[str, float]:
    """Preview puro: no escribe ledger, no muta balances."""
    gross = _money(price)
    platform = _money(gross * PLATFORM_FEE_PCT / 100.0)
    game = _money(gross * GAME_FEE_PCT / 100.0)
    seller = _money(gross - platform - game)
    return {
        "gross": gross,
        "platform_fee": platform,
        "game_fee": game,
        "seller_net": seller,
        "total_fee_pct": PLATFORM_FEE_PCT + GAME_FEE_PCT,
    }
