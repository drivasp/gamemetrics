"""FraudDetectionService — reglas deterministas (sin ML inventado).

Adapter pattern: RuleBasedFraudDetector hoy; ExternalFraudProvider mañana.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Protocol

from checkout.financial_audit import audit_event

_EVENTS: dict[str, deque[tuple[float, str]]] = defaultdict(deque)
_FAILED: dict[str, deque[float]] = defaultdict(deque)
_REFUNDS: dict[str, deque[float]] = defaultdict(deque)
_PAYOUT_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_LOG: list[dict[str, Any]] = []


class FraudDetector(Protocol):
    def evaluate(self, **kwargs) -> dict[str, Any]: ...


class RuleBasedFraudDetector:
    def evaluate(
        self,
        *,
        user_id: str,
        action: str,
        entity_type: str = "",
        entity_id: str = "",
        amount: float = 0,
    ) -> dict[str, Any]:
        now = time.time()
        score = 0
        reasons: list[str] = []

        ev = _EVENTS[user_id]
        while ev and now - ev[0][0] > 600:
            ev.popleft()
        recent_buys = sum(1 for t, a in ev if a in ("purchase", "market_buy", "checkout") and now - t < 120)
        if recent_buys >= 8:
            score += 40
            reasons.append("too_many_purchases_2m")

        if action in ("refund",):
            rq = _REFUNDS[user_id]
            while rq and now - rq[0] > 86400:
                rq.popleft()
            if len(rq) >= 5:
                score += 35
                reasons.append("too_many_refunds_24h")
            rq.append(now)

        if action in ("payout", "payout_attempt"):
            pq = _PAYOUT_ATTEMPTS[user_id]
            while pq and now - pq[0] > 3600:
                pq.popleft()
            if len(pq) >= 5:
                score += 30
                reasons.append("too_many_payout_attempts_1h")
            pq.append(now)

        if action.endswith("_failed"):
            fq = _FAILED[user_id]
            while fq and now - fq[0] > 600:
                fq.popleft()
            fq.append(now)
            if len(fq) >= 6:
                score += 25
                reasons.append("multiple_failed_attempts")

        if amount and amount > 5000:
            score += 15
            reasons.append("high_amount")

        ev.append((now, action))

        if score >= 70:
            action_out = "block"
        elif score >= 40:
            action_out = "review"
        else:
            action_out = "allow"

        row = {
            "user_id": user_id,
            "action_name": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "amount": amount,
            "risk_score": score,
            "reason": ",".join(reasons) or "ok",
            "action": action_out,
            "timestamp": int(now * 1000),
        }
        _LOG.insert(0, row)
        del _LOG[1000:]
        audit_event(
            actor_id=user_id,
            action=f"fraud_{action_out}",
            entity_type=entity_type or "user",
            entity_id=entity_id or user_id,
            amount=amount,
            meta=row,
        )
        return row


class FraudDetectionService:
    """Facade — swap detector without changing callers."""

    def __init__(self, detector: FraudDetector | None = None):
        self.detector = detector or RuleBasedFraudDetector()

    def evaluate(self, **kwargs) -> dict[str, Any]:
        return self.detector.evaluate(**kwargs)

    @staticmethod
    def list_events(limit: int = 100) -> list[dict[str, Any]]:
        return _LOG[:limit]
