"""
Motor de revenue share (take rate) — configurable.

Modos:
- flat (default GameMetrics): un % fijo por partner (ej. publisher 70% → take 30%).
- steam_tiers (opcional): tramos progresivos tipo Steam por lifetime AGR del producto.

Steam tiers (dato de industria / anuncio Valve 2018; verificar en Steamworks Financials):
  ≤ $10M lifetime  → plataforma 30%
  $10M–$50M        → plataforma 25%
  > $50M           → plataforma 20%

Los umbrales NO son retroactivos: solo el ingreso que cae en cada tramo usa ese %.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

MODE = (os.getenv("REVENUE_SHARE_MODE", "flat") or "flat").strip().lower()

# Umbrales Steam-like (USD lifetime Adjusted Gross Revenue por producto).
# Solo se usan si REVENUE_SHARE_MODE=steam_tiers.
TIER_10M = float(os.getenv("RS_TIER_10M_USD", "10000000"))
TIER_50M = float(os.getenv("RS_TIER_50M_USD", "50000000"))
TAKE_BELOW_10M = float(os.getenv("RS_TAKE_BELOW_10M", "30"))
TAKE_10M_50M = float(os.getenv("RS_TAKE_10M_50M", "25"))
TAKE_ABOVE_50M = float(os.getenv("RS_TAKE_ABOVE_50M", "20"))


def _money(value: float | Decimal | str) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class SplitResult:
    gross: float
    platform_fee: float
    publisher_net: float
    platform_take_rate_pct: float
    mode: str
    detail: str


def split_flat(gross: float, publisher_share_pct: float) -> SplitResult:
    share = float(publisher_share_pct if publisher_share_pct is not None else 70.0)
    share = max(0.0, min(100.0, share))
    g = _money(gross)
    publisher_net = _money(g * (share / 100.0))
    platform_fee = _money(g - publisher_net)
    take = _money(100.0 - share)
    return SplitResult(
        gross=g,
        platform_fee=platform_fee,
        publisher_net=publisher_net,
        platform_take_rate_pct=take,
        mode="flat",
        detail=f"flat publisher_share={share}%",
    )


def split_steam_tiers(
    gross: float,
    lifetime_agr_before: float,
) -> SplitResult:
    """
    Aplica take rate progresivo sobre `gross` dada la AGR lifetime ya acumulada
    del producto (antes de esta venta).
    """
    remaining = _money(gross)
    before = max(0.0, float(lifetime_agr_before or 0))
    fee = 0.0
    cursor = before
    parts: list[str] = []

    while remaining > 0.0001:
        if cursor < TIER_10M:
            room = _money(TIER_10M - cursor)
            take_pct = TAKE_BELOW_10M
        elif cursor < TIER_50M:
            room = _money(TIER_50M - cursor)
            take_pct = TAKE_10M_50M
        else:
            room = remaining
            take_pct = TAKE_ABOVE_50M

        slice_amt = _money(min(remaining, room))
        slice_fee = _money(slice_amt * (take_pct / 100.0))
        fee = _money(fee + slice_fee)
        parts.append(f"{slice_amt}@{take_pct}%")
        remaining = _money(remaining - slice_amt)
        cursor = _money(cursor + slice_amt)

    g = _money(gross)
    platform_fee = fee
    publisher_net = _money(g - platform_fee)
    effective_take = _money((platform_fee / g) * 100.0) if g > 0 else 0.0
    return SplitResult(
        gross=g,
        platform_fee=platform_fee,
        publisher_net=publisher_net,
        platform_take_rate_pct=effective_take,
        mode="steam_tiers",
        detail=";".join(parts),
    )


def split_revenue(
    gross: float,
    publisher_share_pct: float = 70.0,
    *,
    lifetime_agr_before: float = 0.0,
) -> SplitResult:
    """
    Punto único de cálculo.
    flat: usa publisher_share_pct del partner.
    steam_tiers: ignora share del partner y usa tramos globales (demo/prod opt-in).
    """
    if MODE == "steam_tiers":
        return split_steam_tiers(gross, lifetime_agr_before)
    return split_flat(gross, publisher_share_pct)


def example_steam_math(lifetime_sales: float) -> dict:
    """Utilidad de documentación / simulador (no escribe ledger)."""
    g = _money(lifetime_sales)
    r = split_steam_tiers(g, 0.0)
    return {
        "lifetime_gross": g,
        "platform_fee": r.platform_fee,
        "publisher_net": r.publisher_net,
        "effective_take_pct": r.platform_take_rate_pct,
        "slices": r.detail,
        "source_note": (
            "Tramos 30/25/20 ampliamente reportados desde anuncio Valve 2018. "
            "Confirmar siempre en Steamworks Financials; no es un SDK público de Valve."
        ),
    }
