"""Steam Wallet — saldo y movimientos (Pinot + Kafka)."""
from __future__ import annotations

import time
import uuid

from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

CREDIT_TYPES = {"topup", "refund", "credit"}
DEBIT_TYPES = {"purchase", "debit"}


async def _balance_from_transactions(user_id: str) -> float:
    """Reconstruye saldo desde movimientos (si la fila de wallet aún no está en Pinot)."""
    rows = await pinot_query(
        f"SELECT amount, tx_type FROM fact_wallet_transactions "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 500"
    )
    bal = 0.0
    for amount, tx_type in rows:
        amt = float(amount or 0)
        t = str(tx_type or "").lower()
        if t in CREDIT_TYPES:
            bal += amt
        elif t in DEBIT_TYPES:
            bal -= amt
    return round(max(0.0, bal), 2)


async def get_balance(user_id: str) -> float:
    rows = await pinot_query(
        f"SELECT balance FROM fact_user_wallets "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if rows:
        return round(float(rows[0][0] or 0), 2)
    return await _balance_from_transactions(user_id)


async def _write_balance(user_id: str, balance: float, now_ms: int) -> None:
    payload = {
        "user_id": user_id,
        "balance": round(float(balance), 2),
        "currency": "USD",
        "updated_at": int(now_ms),
        "deleted": False,
    }
    print(f"[Wallet] write balance user={user_id} balance={payload['balance']}")
    await kafka_send("fact_user_wallets", user_id, payload)


async def apply_transaction(
    user_id: str,
    amount: float,
    tx_type: str,
    reference_id: str = "",
    idempotency_key: str = "",
) -> tuple[float, str]:
    """
    Aplica crédito (amount > 0) o débito (amount < 0).
    tx_type: credit | debit | refund | topup | purchase
    """
    if not idempotency_key:
        idempotency_key = f"{tx_type}_{user_id}_{reference_id}_{uuid.uuid4().hex[:8]}"

    existing = await pinot_query(
        f"SELECT tx_id FROM fact_wallet_transactions "
        f"WHERE idempotency_key = '{esc(idempotency_key)}' AND deleted = false LIMIT 1"
    )
    if existing:
        bal = await get_balance(user_id)
        return bal, existing[0][0]

    balance = await get_balance(user_id)
    new_balance = round(balance + amount, 2)
    if new_balance < -0.001:
        raise ValueError("Saldo insuficiente en la cartera")

    now_ms = int(time.time() * 1000)
    tx_id = uuid.uuid4().hex[:15]
    new_balance = max(0.0, new_balance)

    await kafka_send("fact_wallet_transactions", tx_id, {
        "tx_id": tx_id,
        "user_id": user_id,
        "amount": round(abs(amount), 2),
        "tx_type": tx_type,
        "idempotency_key": idempotency_key,
        "reference_id": reference_id or "",
        "created_at": now_ms,
        "deleted": False,
    })
    await _write_balance(user_id, new_balance, now_ms)
    return new_balance, tx_id


async def list_transactions(user_id: str, limit: int = 50) -> list[dict]:
    rows = await pinot_query(
        f"SELECT tx_id, amount, tx_type, reference_id, created_at "
        f"FROM fact_wallet_transactions "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    return [
        {
            "tx_id": r[0],
            "amount": float(r[1] or 0),
            "tx_type": r[2],
            "reference_id": r[3] or "",
            "created_at": str(r[4]),
        }
        for r in rows
    ]
