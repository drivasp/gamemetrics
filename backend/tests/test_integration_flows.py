"""
Integration tests for financial + marketplace flows (no Docker required for core logic).

Run:
  cd backend && python tests/test_integration_flows.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Stub kafka BEFORE importing marketplace/fraud modules that pull it
async def _noop_send(*a, **k):
    return True

_kp = types.ModuleType("shared.kafka_producer")
_kp.kafka_send = _noop_send
_kp.start_producer = _noop_send
_kp.stop_producer = _noop_send
sys.modules["shared.kafka_producer"] = _kp

# Stub auth_deps esc if pulled
if "shared.auth_deps" not in sys.modules:
    _ad = types.ModuleType("shared.auth_deps")

    def esc(s):
        return str(s).replace("'", "")

    _ad.esc = esc
    _ad.require_token = lambda *a, **k: ("", "u")
    sys.modules["shared.auth_deps"] = _ad

from checkout.revenue_share import split_flat  # noqa: E402
from checkout.webhook_idempotency import process_once  # noqa: E402
from tax.engine import calculate_tax  # noqa: E402
from fraud.service import RuleBasedFraudDetector  # noqa: E402
from marketplace import service as market  # noqa: E402
from marketplace import durable_store as mstore  # noqa: E402
from marketplace.service import (  # noqa: E402
    mint_item,
    create_listing,
    purchase_listing,
)
from ledger.sqlite_store import init_ledger  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402


def _reset_mkt_db():
    tmp = Path(tempfile.mkdtemp(prefix="gm_int_"))
    os.environ["FINANCIAL_LEDGER_PATH"] = str(tmp / "ledger.sqlite3")
    import ledger.sqlite_store as ls

    ls._INITIALIZED = False
    init_ledger()
    mstore._INITIALIZED = False
    p = Path(mstore._db_path())
    if p.exists():
        p.unlink()
    mstore.init_marketplace_store()


def sale_ledger_id(order_id: str, product_id: str) -> str:
    return f"sale_{order_id}_{product_id}"[:64]


def refund_ledger_id(purchase_id: str) -> str:
    return f"refund_{purchase_id}"[:64]


def chargeback_ledger_id(payment_id: str, product_id: str = "") -> str:
    raw = f"cb_{payment_id}_{product_id}" if product_id else f"cb_{payment_id}"
    return raw[:64]


def split_revenue(gross: float, publisher_share_pct: float):
    r = split_flat(gross, publisher_share_pct)
    return r.gross, r.platform_fee, r.publisher_net, r.platform_take_rate_pct


_WALLETS: dict[str, float] = {}
_WALLET_TX: dict[str, str] = {}


async def fake_get_balance(user_id: str) -> float:
    return _WALLETS.get(user_id, 0.0)


async def fake_apply_transaction(user_id, amount, tx_type, reference_id="", idempotency_key=""):
    if idempotency_key and idempotency_key in _WALLET_TX:
        return _WALLETS.get(user_id, 0.0), _WALLET_TX[idempotency_key]
    bal = _WALLETS.get(user_id, 0.0) + amount
    if bal < -0.001:
        raise ValueError("Saldo insuficiente en la cartera")
    _WALLETS[user_id] = round(max(0.0, bal), 2)
    tx = idempotency_key or f"tx_{user_id}_{len(_WALLET_TX)}"
    _WALLET_TX[idempotency_key or tx] = tx
    return _WALLETS[user_id], tx


market.get_balance = fake_get_balance  # type: ignore
market.apply_transaction = fake_apply_transaction  # type: ignore


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_revenue_share_flow():
    g, fee, net, take = split_revenue(20.0, 70.0)
    assert fee == 6.0 and net == 14.0


def test_tax_engine_mx_and_es_included():
    mx = calculate_tax(100, "MX", order_id="o1")
    assert mx["tax_amount"] == 16.0 and mx["total_with_tax"] == 116.0
    es = calculate_tax(121, "ES", order_id="o2")
    assert es["tax_included_in_price"] is True
    assert abs(es["tax_amount"] - 21.0) < 0.05


def test_webhook_idempotency():
    _reset_mkt_db()
    calls = {"n": 0}

    def handler():
        calls["n"] += 1
        return {"paid": 10}

    r1, dup1 = process_once("evt_1", handler)
    r2, dup2 = process_once("evt_1", handler)
    assert calls["n"] == 1 and dup1 is False and dup2 is True and r1 == r2


def test_marketplace_buy_idempotent_and_fees():
    _WALLETS.clear()
    _WALLET_TX.clear()
    _reset_mkt_db()

    seller = "seller1"
    buyer = "buyer1"
    _WALLETS[buyer] = 100.0
    _WALLETS[seller] = 0.0

    item = run(market.mint_item(owner_user_id=seller, game_id="g1", item_name="Skin Red"))
    listing = run(market.create_listing(seller_user_id=seller, item_id=item["item_id"], price_usd=10))
    tx1 = run(market.purchase_listing(buyer_user_id=buyer, listing_id=listing["listing_id"], idempotency_key="k1"))
    tx2 = run(market.purchase_listing(buyer_user_id=buyer, listing_id=listing["listing_id"], idempotency_key="k1"))
    assert tx1["tx_id"] == tx2["tx_id"]
    assert abs(tx1["platform_fee"] + tx1["game_fee"] + tx1["seller_net"] - 10) < 0.02
    assert abs(_WALLETS[buyer] - 90.0) < 0.02
    assert abs(_WALLETS[seller] - tx1["seller_net"]) < 0.02
    assert mstore.get_item(item["item_id"])["owner_user_id"] == buyer


def test_marketplace_double_buy_blocked():
    _WALLETS.clear()
    _reset_mkt_db()
    seller, buyer, buyer2 = "s2", "b2", "b3"
    _WALLETS[buyer] = 50
    _WALLETS[buyer2] = 50
    item = run(market.mint_item(owner_user_id=seller, game_id="g1", item_name="Sword"))
    listing = run(market.create_listing(seller_user_id=seller, item_id=item["item_id"], price_usd=5))
    run(market.purchase_listing(buyer_user_id=buyer, listing_id=listing["listing_id"], idempotency_key="a"))
    try:
        run(market.purchase_listing(buyer_user_id=buyer2, listing_id=listing["listing_id"], idempotency_key="b"))
        raise AssertionError("should fail")
    except ValueError:
        pass


def test_fraud_blocks_after_many_events():
    det = RuleBasedFraudDetector()
    uid = "fraud_user_x"
    last = None
    for i in range(10):
        last = det.evaluate(user_id=uid, action="checkout", entity_id=str(i), amount=10)
    assert last["risk_score"] >= 40


def test_chargeback_and_sale_ids_stable():
    assert sale_ledger_id("o", "p") == sale_ledger_id("o", "p")
    assert refund_ledger_id("x") == refund_ledger_id("x")
    assert chargeback_ledger_id("pay", "p") == chargeback_ledger_id("pay", "p")


def test_wallet_debit_credit_conceptual():
    r = split_flat(20, 70)
    assert r.platform_fee == 6 and r.publisher_net == 14


if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    if failed:
        sys.exit(1)
    print(f"OK {len(tests)} integration tests")
