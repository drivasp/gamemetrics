"""Steam Wallet — saldo desde ledger durable; Kafka/Pinot = analytics/event bus."""
from __future__ import annotations

import time
import uuid

from ledger.sqlite_store import account_balance, get_by_idempotency, post_entry
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

CREDIT_TYPES = {"topup", "refund", "credit"}
DEBIT_TYPES = {"purchase", "debit"}


async def get_balance(user_id: str) -> float:
    """Source of truth: SUM(movimientos) en SQLite ledger."""
    return account_balance("user_wallet", user_id, "USD")


async def _write_balance_analytics(user_id: str, balance: float, now_ms: int) -> None:
    """Proyección eventual a Pinot (no SoT)."""
    payload = {
        "user_id": user_id,
        "balance": round(float(balance), 2),
        "currency": "USD",
        "updated_at": int(now_ms),
        "deleted": False,
    }
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
    Idempotente vía UNIQUE(idempotency_key) en ledger durable.
    """
    if not idempotency_key:
        idempotency_key = f"{tx_type}_{user_id}_{reference_id}_{uuid.uuid4().hex[:8]}"

    existing = get_by_idempotency(idempotency_key)
    if existing:
        return await get_balance(user_id), existing["transaction_id"]

    # Normalizar signo según tipo
    t = str(tx_type or "").lower()
    raw = float(amount)
    if t in CREDIT_TYPES:
        signed = abs(raw)
    elif t in DEBIT_TYPES:
        signed = -abs(raw)
    else:
        signed = raw

    entry = post_entry(
        entry_type=t or "adjustment",
        account_type="user_wallet",
        account_id=user_id,
        amount=signed,
        currency="USD",
        reference=reference_id or "",
        idempotency_key=idempotency_key,
        metadata={"tx_type": t},
        allow_negative_balance=False,
    )
    tx_id = entry["transaction_id"]
    now_ms = int(entry["created_at"] or time.time() * 1000)
    new_balance = await get_balance(user_id)

    # Event bus + analytics (best effort; no afecta SoT)
    try:
        await kafka_send("fact_wallet_transactions", tx_id, {
            "tx_id": tx_id,
            "user_id": user_id,
            "amount": round(abs(signed), 2),
            "tx_type": t,
            "idempotency_key": idempotency_key,
            "reference_id": reference_id or "",
            "created_at": now_ms,
            "deleted": False,
        })
        await _write_balance_analytics(user_id, new_balance, now_ms)
    except Exception as exc:
        print(f"[Wallet] analytics kafka skip: {exc}")

    return new_balance, tx_id


async def list_transactions(user_id: str, limit: int = 50) -> list[dict]:
    from ledger.sqlite_store import list_entries

    entries = list_entries("user_wallet", user_id, limit=limit)
    if entries:
        return [
            {
                "tx_id": e["transaction_id"],
                "amount": abs(float(e["amount"] or 0)),
                "tx_type": e["type"],
                "reference_id": e.get("reference") or "",
                "created_at": str(e.get("created_at") or ""),
            }
            for e in entries
        ]
    # Fallback analytics Pinot (legacy)
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
