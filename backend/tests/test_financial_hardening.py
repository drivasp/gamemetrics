"""
Blindaje financiero — tests de los 8 riesgos de AUDITORIA_GAMEMETRICS.md
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp(prefix="gm_hard_")
os.environ["FINANCIAL_LEDGER_PATH"] = str(Path(_tmp) / "ledger.sqlite3")

import ledger.sqlite_store as store  # noqa: E402

store._INITIALIZED = False
store.init_ledger()


def test_try_claim_idempotent_fulfill():
    assert store.try_claim("fulfill_order_o1", "fulfill_order") is True
    assert store.try_claim("fulfill_order_o1", "fulfill_order") is False
    assert store.claim_exists("fulfill_order_o1")


def test_concurrent_claims_only_one_wins():
    key = "fulfill_order_race"
    wins = []

    def worker():
        wins.append(store.try_claim(key, "fulfill_order"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for w in wins if w) == 1


def test_wallet_requires_idempotency_key():
    import asyncio
    import types

    if "shared.auth_deps" not in sys.modules:
        _ad = types.ModuleType("shared.auth_deps")
        _ad.esc = lambda s: str(s).replace("'", "")
        sys.modules["shared.auth_deps"] = _ad
    if "shared.cliente_pinot" not in sys.modules:
        _cp = types.ModuleType("shared.cliente_pinot")

        async def _pq(*a, **k):
            return []

        _cp.pinot_query = _pq
        sys.modules["shared.cliente_pinot"] = _cp
    if "shared.kafka_producer" not in sys.modules:
        _kp = types.ModuleType("shared.kafka_producer")

        async def _ks(*a, **k):
            return True

        _kp.kafka_send = _ks
        sys.modules["shared.kafka_producer"] = _kp

    from wallet.servicio import apply_transaction

    async def go():
        try:
            await apply_transaction("u1", 10, "topup", reference_id="r")
            raise AssertionError("should require key")
        except ValueError as e:
            assert "idempotency_key" in str(e).lower()

    asyncio.run(go())


def test_wallet_idempotent_no_double():
    import asyncio
    import types

    if "shared.auth_deps" not in sys.modules:
        _ad = types.ModuleType("shared.auth_deps")
        _ad.esc = lambda s: str(s).replace("'", "")
        sys.modules["shared.auth_deps"] = _ad
    if "shared.cliente_pinot" not in sys.modules:
        _cp = types.ModuleType("shared.cliente_pinot")

        async def _pq(*a, **k):
            return []

        _cp.pinot_query = _pq
        sys.modules["shared.cliente_pinot"] = _cp
    if "shared.kafka_producer" not in sys.modules:
        _kp = types.ModuleType("shared.kafka_producer")

        async def _ks(*a, **k):
            return True

        _kp.kafka_send = _ks
        sys.modules["shared.kafka_producer"] = _kp

    from wallet.servicio import apply_transaction, get_balance

    async def go():
        await apply_transaction("u2", 20, "topup", idempotency_key="top_u2")
        await apply_transaction("u2", 20, "topup", idempotency_key="top_u2")
        assert await get_balance("u2") == 20.0

    asyncio.run(go())


def test_refund_wallet_key_stable_by_purchase():
    import hashlib

    pid = "user_prod1"
    digest = hashlib.sha256(f"refund:{pid}".encode()).hexdigest()
    rid = f"rf_{digest[:13]}"
    key = f"refund_wallet_{pid}"
    assert rid.startswith("rf_")
    a = store.post_entry(
        entry_type="refund",
        account_type="user_wallet",
        account_id="user",
        amount=5,
        idempotency_key=key,
    )
    b = store.post_entry(
        entry_type="refund",
        account_type="user_wallet",
        account_id="user",
        amount=5,
        idempotency_key=key,
    )
    assert a["transaction_id"] == b["transaction_id"]
    assert store.account_balance("user_wallet", "user") == 5.0


def test_webhook_process_once_durable():
    from checkout.webhook_idempotency import process_once

    n = {"c": 0}

    def h():
        n["c"] += 1
        return {"ok": True}

    r1, d1 = process_once("evt_hard_1", h)
    r2, d2 = process_once("evt_hard_1", h)
    assert n["c"] == 1 and d1 is False and d2 is True


def test_enqueue_reconcile_not_just_print():
    qid = store.enqueue_reconcile(
        operation="durable_sale",
        entity_id="sale_x",
        error_message="boom",
        payload={"order_id": "o"},
    )
    pending = store.list_reconcile_pending()
    assert any(p["queue_id"] == qid for p in pending)


def test_marketplace_durable_survives_reinit():
    from marketplace import durable_store as ms

    ms._INITIALIZED = False
    ms.init_marketplace_store()
    ms.save_item(
        {
            "item_id": "i1",
            "owner_user_id": "u",
            "status": "owned",
            "deleted": False,
            "game_id": "g",
            "item_name": "X",
        }
    )
    ms._INITIALIZED = False
    ms.init_marketplace_store()
    assert ms.get_item("i1")["owner_user_id"] == "u"


def test_payout_requires_key():
    import asyncio
    import types

    # Minimal stubs already in payout test file — invoke ValueError path
    from checkout import partner_payouts as pp

    async def fake_bal(pid):
        return {"balance_available": 100, "balance_pending": 0, "hold_days": 0, "payout_min_usd": 1}

    async def empty(*a, **k):
        return []

    async def noop(*a, **k):
        return True

    pp.partner_balance = fake_bal
    pp.list_partner_payouts = empty
    pp.kafka_send = noop

    class _F:
        def evaluate(self, **k):
            return {"action": "allow", "reason": "ok", "risk_score": 0}

    import fraud.service as fs

    fs.FraudDetectionService = _F  # type: ignore

    async def go():
        try:
            await pp.create_payout(
                partner_id="px",
                amount=10,
                created_by="a",
                method="manual",
                reference="",
                idempotency_key="",
            )
            raise AssertionError("should require key")
        except ValueError as e:
            assert "idempotency" in str(e).lower() or "reference" in str(e).lower()

    asyncio.run(go())


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("OK financial hardening tests")
