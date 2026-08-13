"""
Marketplace P2P — diseño (NO implementado en producción).

Steam Community Market: transacciones entre usuarios con fee de plataforma
(el % exacto suele mostrarse en la UI de Steam; Valve no publicó un único
documento Steamworks limpio con el % en la consulta de esta investigación —
tratar fee concreto como dependencia de producto/legal).

GameMetrics: arquitectura preparada. Activar solo tras anti-fraude + AML (D10).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketplaceFeePolicy:
    """Política propuesta — decisión empresarial pendiente."""

    platform_fee_pct: float = 5.0  # PROPUESTA, no dato Steam oficial
    game_fee_pct: float = 10.0  # PROPUESTA (análogo a fee del juego en Steam)
    currency: str = "USD"
    trade_hold_days: int = 7
    enabled: bool = False

    @property
    def total_fee_pct(self) -> float:
        return self.platform_fee_pct + self.game_fee_pct


def propose_settlement(price: float, policy: MarketplaceFeePolicy | None = None) -> dict:
    """
    Calcula desglose conceptual de una venta P2P.
    No escribe ledger — el marketplace aún no está habilitado.
    """
    p = policy or MarketplaceFeePolicy()
    if not p.enabled:
        return {
            "enabled": False,
            "message": "Marketplace deshabilitado (OPEN_DEPENDENCIES D10).",
            "policy": {
                "platform_fee_pct": p.platform_fee_pct,
                "game_fee_pct": p.game_fee_pct,
                "total_fee_pct": p.total_fee_pct,
                "trade_hold_days": p.trade_hold_days,
                "note": "Porcentajes = PROPUESTA GameMetrics, no cifra oficial Valve.",
            },
        }
    gross = round(float(price), 2)
    platform = round(gross * (p.platform_fee_pct / 100.0), 2)
    game = round(gross * (p.game_fee_pct / 100.0), 2)
    seller_net = round(gross - platform - game, 2)
    return {
        "enabled": True,
        "gross": gross,
        "platform_fee": platform,
        "game_fee": game,
        "seller_net": seller_net,
        "buyer_pays": gross,
    }
