"""
Pruebas de integridad financiera (sin Pinot/Kafka ni deps pesadas).

Ejecutar:
  cd backend && python tests/test_financial_integrity.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Solo motor puro (no importa FastAPI/bcrypt/Pinot)
from checkout.revenue_share import (  # noqa: E402
    split_flat,
    split_steam_tiers,
    example_steam_math,
    split_revenue,
)


def sale_ledger_id(order_id: str, product_id: str) -> str:
    return f"sale_{order_id}_{product_id}"[:64]


def refund_ledger_id(purchase_id: str) -> str:
    return f"refund_{purchase_id}"[:64]


def chargeback_ledger_id(payment_id: str, product_id: str = "") -> str:
    raw = f"cb_{payment_id}_{product_id}" if product_id else f"cb_{payment_id}"
    return raw[:64]


def test_split_flat_10_dollar_game():
    r = split_flat(10.0, 70.0)
    assert r.gross == 10.0
    assert r.publisher_net == 7.0
    assert r.platform_fee == 3.0
    assert r.platform_take_rate_pct == 30.0


def test_split_flat_20_and_50():
    assert split_flat(20, 70).publisher_net == 14.0
    assert split_flat(50, 70).platform_fee == 15.0


def test_steam_tiers_progressive_not_retroactive():
    r = split_steam_tiers(12_000_000, 0.0)
    fee = 10_000_000 * 0.30 + 2_000_000 * 0.25
    assert abs(r.platform_fee - fee) < 0.02
    assert abs(r.publisher_net - (12_000_000 - fee)) < 0.02


def test_steam_tiers_crossing_from_prior():
    r = split_steam_tiers(1_000_000, 9_500_000)
    expected_fee = 500_000 * 0.30 + 500_000 * 0.25
    assert abs(r.platform_fee - expected_fee) < 0.02


def test_steam_tiers_above_50m():
    r = split_steam_tiers(1_000_000, 50_000_000)
    assert abs(r.platform_fee - 200_000.0) < 0.02


def test_example_math_10m():
    ex = example_steam_math(10_000_000)
    assert ex["platform_fee"] == 3_000_000.0
    assert ex["publisher_net"] == 7_000_000.0


def test_example_math_60m():
    ex = example_steam_math(60_000_000)
    assert abs(ex["platform_fee"] - 15_000_000) < 1.0


def test_idempotent_ids_stable():
    assert sale_ledger_id("ord1", "prodA") == sale_ledger_id("ord1", "prodA")
    assert refund_ledger_id("p1") == refund_ledger_id("p1")
    assert chargeback_ledger_id("pay1", "prodA") == chargeback_ledger_id("pay1", "prodA")


def test_compat_split_revenue():
    r = split_revenue(100.0, 70.0)
    assert r.gross == 100.0 and r.platform_fee == 30.0 and r.publisher_net == 70.0


def test_conceptual_pipeline_1000_sales():
    gross = 1000.0
    refunds = 50.0  # SUPUESTO
    chargebacks = 0.0  # SUPUESTO
    agr = gross - refunds - chargebacks
    r = split_flat(agr, 70.0)
    assert r.platform_fee == 285.0
    assert r.publisher_net == 665.0


if __name__ == "__main__":
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
    print(f"OK {len(tests)} tests")
