"""
Tests del ledger durable + fees públicos sin mutar dinero.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Isolated DB for this process
_tmp = tempfile.mkdtemp(prefix="gm_ledger_")
os.environ["FINANCIAL_LEDGER_PATH"] = str(Path(_tmp) / "test_ledger.sqlite3")

# Reset module init flag if already imported
import ledger.sqlite_store as store  # noqa: E402

store._INITIALIZED = False
store.init_ledger()


def test_post_idempotent_no_double_money():
    a = store.post_entry(
        entry_type="topup",
        account_type="user_wallet",
        account_id="u1",
        amount=50,
        idempotency_key="top_u1_1",
    )
    b = store.post_entry(
        entry_type="topup",
        account_type="user_wallet",
        account_id="u1",
        amount=50,
        idempotency_key="top_u1_1",
    )
    assert a["transaction_id"] == b["transaction_id"]
    assert store.account_balance("user_wallet", "u1") == 50.0


def test_debit_insufficient():
    store.post_entry(
        entry_type="topup",
        account_type="user_wallet",
        account_id="u2",
        amount=10,
        idempotency_key="top_u2",
    )
    try:
        store.post_entry(
            entry_type="purchase",
            account_type="user_wallet",
            account_id="u2",
            amount=-50,
            idempotency_key="buy_u2",
        )
        raise AssertionError("should fail")
    except ValueError:
        pass
    assert store.account_balance("user_wallet", "u2") == 10.0


def test_balance_equals_sum():
    store.post_entry(
        entry_type="topup", account_type="user_wallet", account_id="u3",
        amount=100, idempotency_key="t3a",
    )
    store.post_entry(
        entry_type="purchase", account_type="user_wallet", account_id="u3",
        amount=-30, idempotency_key="t3b",
    )
    store.post_entry(
        entry_type="refund", account_type="user_wallet", account_id="u3",
        amount=10, idempotency_key="t3c",
    )
    assert store.account_balance("user_wallet", "u3") == 80.0


def test_fees_preview_pure_function_no_ledger_write():
    from marketplace.fees_calc import fee_breakdown

    before = len(store.list_entries(limit=1000))
    fee_breakdown(10)
    fee_breakdown(99.99)
    after = len(store.list_entries(limit=1000))
    assert before == after
    assert fee_breakdown(10)["gross"] == 10.0
    assert fee_breakdown(10)["seller_net"] == 8.5  # 5%+10% default


def test_architecture_note():
    n = store.architecture_note()
    assert "source_of_truth" in n and "Kafka" in n["event_bus"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("OK durable ledger tests")
