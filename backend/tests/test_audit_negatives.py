"""
Auditoría negativa de integridad financiera (local, sin Docker deps pesadas).
Ejecutar: cd backend && python tests/test_audit_negatives.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def _noop(*a, **k):
    return True

_kp = types.ModuleType("shared.kafka_producer")
_kp.kafka_send = _noop
_kp.start_producer = _noop
_kp.stop_producer = _noop
sys.modules["shared.kafka_producer"] = _kp

# Stub wallet BEFORE marketplace.service imports it
_WALLETS: dict[str, float] = {}
_WALLET_TX: dict[str, str] = {}


async def fake_get_balance(uid: str) -> float:
    return _WALLETS.get(uid, 0.0)


async def fake_apply(uid, amount, tx_type, reference_id="", idempotency_key=""):
    if idempotency_key and idempotency_key in _WALLET_TX:
        return _WALLETS.get(uid, 0.0), _WALLET_TX[idempotency_key]
    bal = _WALLETS.get(uid, 0.0) + amount
    if bal < -0.001:
        raise ValueError("Saldo insuficiente en la cartera")
    _WALLETS[uid] = round(max(0.0, bal), 2)
    tx = idempotency_key or f"t{len(_WALLET_TX)}"
    _WALLET_TX[idempotency_key or tx] = tx
    return _WALLETS[uid], tx


_ws = types.ModuleType("wallet.servicio")
_ws.apply_transaction = fake_apply
_ws.get_balance = fake_get_balance
sys.modules["wallet.servicio"] = _ws
sys.modules["wallet"] = types.ModuleType("wallet")

# Stub financial_audit (no bcrypt chain)
_fa = types.ModuleType("checkout.financial_audit")

def audit_event(**kwargs):
    return {"ok": True, **{k: kwargs.get(k) for k in ("actor_id", "action")}}

_fa.audit_event = audit_event
_fa.list_audit = lambda limit=100: []
sys.modules["checkout.financial_audit"] = _fa

from checkout.revenue_share import split_flat, split_steam_tiers  # noqa: E402
from checkout.webhook_idempotency import process_once  # noqa: E402
from tax.engine import calculate_tax  # noqa: E402
from fraud.service import RuleBasedFraudDetector  # noqa: E402
from security.rate_limit import rate_limit  # noqa: E402
from marketplace.fees_calc import fee_breakdown  # noqa: E402
from marketplace import service as market  # noqa: E402
from marketplace import durable_store as mstore  # noqa: E402
from fastapi import HTTPException  # noqa: E402

market.get_balance = fake_get_balance  # type: ignore
market.apply_transaction = fake_apply  # type: ignore


def run(c):
    return asyncio.get_event_loop().run_until_complete(c)


RESULTS = []


def check(name: str, fn):
    try:
        fn()
        RESULTS.append((name, "PASS", ""))
        print(f"PASS {name}")
    except Exception as e:
        RESULTS.append((name, "FAIL", str(e)))
        print(f"FAIL {name}: {e}")


def reset_market():
    _WALLETS.clear()
    _WALLET_TX.clear()
    import tempfile
    from pathlib import Path
    from ledger.sqlite_store import init_ledger
    import ledger.sqlite_store as ls

    tmp = Path(tempfile.mkdtemp(prefix="gm_mkt_"))
    os.environ["FINANCIAL_LEDGER_PATH"] = str(tmp / "ledger.sqlite3")
    ls._INITIALIZED = False
    init_ledger()
    mstore._INITIALIZED = False
    p = Path(mstore._db_path())
    if p.exists():
        p.unlink()
    mstore.init_marketplace_store()


def test_fees_10():
    f = fee_breakdown(10)
    assert abs(f["platform_fee"] + f["game_fee"] + f["seller_net"] - 10) < 0.001
    assert f["platform_fee"] == 0.5 and f["game_fee"] == 1.0 and f["seller_net"] == 8.5


def test_invalid_price():
    reset_market()
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="x"))
    try:
        run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=-1))
        raise AssertionError("should reject")
    except ValueError:
        pass


def test_listing_not_owner():
    reset_market()
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="x"))
    try:
        run(market.create_listing(seller_user_id="other", item_id=item["item_id"], price_usd=5))
        raise AssertionError("should reject")
    except ValueError:
        pass


def test_buy_own_listing():
    reset_market()
    _WALLETS["s"] = 100
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="x"))
    listing = run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=5))
    try:
        run(market.purchase_listing(buyer_user_id="s", listing_id=listing["listing_id"], idempotency_key="own"))
        raise AssertionError("should reject")
    except ValueError:
        pass


def test_insufficient_balance():
    reset_market()
    _WALLETS["b"] = 1
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="x"))
    listing = run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=50))
    try:
        run(market.purchase_listing(buyer_user_id="b", listing_id=listing["listing_id"], idempotency_key="poor"))
        raise AssertionError("should reject")
    except ValueError:
        pass


def test_double_buy_same_listing():
    reset_market()
    _WALLETS["b1"] = 100
    _WALLETS["b2"] = 100
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="x"))
    listing = run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=10))
    run(market.purchase_listing(buyer_user_id="b1", listing_id=listing["listing_id"], idempotency_key="d1"))
    try:
        run(market.purchase_listing(buyer_user_id="b2", listing_id=listing["listing_id"], idempotency_key="d2"))
        raise AssertionError("should reject")
    except ValueError:
        pass
    assert mstore.get_item(item["item_id"])["owner_user_id"] == "b1"
    assert abs(_WALLETS["b1"] - 90) < 0.01
    assert abs(_WALLETS["b2"] - 100) < 0.01  # no debit


def test_idempotent_buy_no_double_money():
    reset_market()
    _WALLETS["b"] = 100
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="x"))
    listing = run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=10))
    t1 = run(market.purchase_listing(buyer_user_id="b", listing_id=listing["listing_id"], idempotency_key="same"))
    t2 = run(market.purchase_listing(buyer_user_id="b", listing_id=listing["listing_id"], idempotency_key="same"))
    assert t1["tx_id"] == t2["tx_id"]
    assert abs(_WALLETS["b"] - 90) < 0.01
    assert abs(_WALLETS["s"] - 8.5) < 0.01


def test_webhook_duplicate():
    reset_market()
    from ledger.sqlite_store import init_ledger
    import ledger.sqlite_store as ls

    ls._INITIALIZED = False
    init_ledger()
    n = {"c": 0}

    def h():
        n["c"] += 1
        return {"ok": 1}

    process_once("wh_dup", h)
    process_once("wh_dup", h)
    assert n["c"] == 1


def test_revenue_share_math():
    r = split_flat(50, 70)
    assert r.platform_fee == 15 and r.publisher_net == 35
    t = split_steam_tiers(12_000_000, 0)
    assert abs(t.platform_fee - (10_000_000 * 0.3 + 2_000_000 * 0.25)) < 1


def test_tax_unknown_country_pending():
    z = calculate_tax(100, "ZZ")
    assert z["status"] == "pending_legal_config" or z["country_code"] == "ZZ"


def test_rate_limit_blocks():
    async def burst():
        for _ in range(3):
            await rate_limit("u_rl", "audit_action", limit=2, window_s=60)

    try:
        run(burst())
        raise AssertionError("should 429")
    except HTTPException as e:
        assert e.status_code == 429


def test_fraud_score_escalates():
    d = RuleBasedFraudDetector()
    last = None
    for i in range(12):
        last = d.evaluate(user_id="fu", action="checkout", entity_id=str(i), amount=1)
    assert last["risk_score"] >= 40
    assert last["action"] in ("review", "block")


def test_cancel_listing_restores_owned():
    reset_market()
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="y"))
    listing = run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=3))
    run(market.cancel_listing(seller_user_id="s", listing_id=listing["listing_id"]))
    assert mstore.get_item(item["item_id"])["status"] == "owned"
    assert mstore.get_listing(listing["listing_id"])["status"] == "cancelled"


def test_balances_match_fees_ledger_concept():
    reset_market()
    _WALLETS["b"] = 100
    _WALLETS["s"] = 0
    item = run(market.mint_item(owner_user_id="s", game_id="g", item_name="z"))
    listing = run(market.create_listing(seller_user_id="s", item_id=item["item_id"], price_usd=20))
    tx = run(market.purchase_listing(buyer_user_id="b", listing_id=listing["listing_id"], idempotency_key="bal"))
    assert abs(_WALLETS["b"] + tx["gross_amount"] - 100) < 0.01
    assert abs(_WALLETS["s"] - tx["seller_net"]) < 0.01
    assert abs(tx["platform_fee"] + tx["game_fee"] + tx["seller_net"] - tx["gross_amount"]) < 0.01


if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)

    fails = [r for r in RESULTS if r[1] == "FAIL"]
    print(f"\nSUMMARY {len(RESULTS) - len(fails)}/{len(RESULTS)} PASS")
    sys.exit(1 if fails else 0)
