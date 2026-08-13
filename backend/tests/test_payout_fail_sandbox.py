"""Smoke: payout sandbox_fail no debita y es idempotente por reference."""
from __future__ import annotations

import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="gm_payout_")
os.environ["FINANCIAL_LEDGER_PATH"] = str(Path(_tmp) / "ledger.sqlite3")


async def _noop(*a, **k):
    return True


_kp = types.ModuleType("shared.kafka_producer")
_kp.kafka_send = _noop
sys.modules["shared.kafka_producer"] = _kp

_ad = types.ModuleType("shared.auth_deps")
_ad.esc = lambda s: str(s).replace("'", "")
sys.modules.setdefault("shared.auth_deps", _ad)

_cp = types.ModuleType("shared.cliente_pinot")


async def _pinot(*a, **k):
    return []


_cp.pinot_query = _pinot
sys.modules["shared.cliente_pinot"] = _cp

_pl = types.ModuleType("checkout.partner_ledger")
_pl.list_partner_ledger = _pinot
_pl.record_sale_ledger = _pinot
sys.modules["checkout.partner_ledger"] = _pl

_fa = types.ModuleType("checkout.financial_audit")
_fa.audit_event = lambda **k: {}
sys.modules["checkout.financial_audit"] = _fa

_fr = types.ModuleType("fraud.service")


class _F:
    def evaluate(self, **k):
        return {"action": "allow", "reason": "ok", "risk_score": 0}


_fr.FraudDetectionService = _F
sys.modules["fraud.service"] = _fr
sys.modules["fraud"] = types.ModuleType("fraud")

from checkout import partner_payouts as pp  # noqa: E402


async def fake_balance(pid):
    return {
        "balance_available": 500.0,
        "balance_pending": 0.0,
        "hold_days": 0,
        "payout_min_usd": float(getattr(pp, "PAYOUT_MIN_USD", 1)),
    }


async def empty_payouts(partner_id, limit=100):
    return [p for p in pp._PAYOUT_CACHE.values() if p.get("partner_id") == partner_id]


async def main():
    pp.partner_balance = fake_balance
    pp.list_partner_payouts = empty_payouts
    pp.kafka_send = _noop
    pp._PAYOUT_CACHE.clear()
    pp._PAYOUTS_BY_PARTNER.clear()

    row = await pp.create_payout(
        partner_id="p1",
        amount=50,
        created_by="admin",
        method="sandbox_fail",
        reference="fail-1",
    )
    assert row["status"] == "failed", row
    assert row["paid_at"] == 0

    row2 = await pp.create_payout(
        partner_id="p1",
        amount=50,
        created_by="admin",
        method="sandbox_fail",
        reference="fail-1",
    )
    assert row2["payout_id"] == row["payout_id"], (row, row2)
    print("PASS payout_sandbox_fail_no_debit_and_idempotent")


if __name__ == "__main__":
    asyncio.run(main())
