"""
Ledger financiero durable (SQLite WAL) — SOURCE OF TRUTH de dinero.

Arquitectura:
  SQLite ledger  = source of truth transaccional (balances reconstruibles)
  Kafka          = event bus (replicación / side effects)
  Pinot          = analytics / lecturas operativas eventuales

NO es un ledger bancario regulado ni sustituye PCI/PSP.
Idempotencia: UNIQUE(idempotency_key) impide doble posteo.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

_DEFAULT_PATH = os.getenv(
    "FINANCIAL_LEDGER_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "financial_ledger.sqlite3"),
)
_LOCK = threading.RLock()
_INITIALIZED = False


def _money(v: float | Decimal | str) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def ledger_path() -> str:
    return os.getenv("FINANCIAL_LEDGER_PATH", _DEFAULT_PATH)


def _connect() -> sqlite3.Connection:
    path = ledger_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def _tx():
    with _LOCK:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            yield conn
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        finally:
            conn.close()


def init_ledger() -> None:
    global _INITIALIZED
    with _LOCK:
        path = ledger_path()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_transactions (
                    transaction_id   TEXT PRIMARY KEY,
                    type             TEXT NOT NULL,
                    account_type     TEXT NOT NULL,
                    account_id       TEXT NOT NULL,
                    amount           REAL NOT NULL,
                    currency         TEXT NOT NULL DEFAULT 'USD',
                    reference        TEXT NOT NULL DEFAULT '',
                    related_order    TEXT NOT NULL DEFAULT '',
                    related_payment  TEXT NOT NULL DEFAULT '',
                    status           TEXT NOT NULL DEFAULT 'posted',
                    created_at       INTEGER NOT NULL,
                    idempotency_key  TEXT NOT NULL,
                    metadata_json    TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(idempotency_key)
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ft_account "
                "ON financial_transactions(account_type, account_id, status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ft_created "
                "ON financial_transactions(created_at);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ft_type "
                "ON financial_transactions(type);"
            )
        finally:
            conn.close()
        _INITIALIZED = True


def ensure_init() -> None:
    if not _INITIALIZED:
        init_ledger()


def get_by_idempotency(idempotency_key: str) -> dict[str, Any] | None:
    ensure_init()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM financial_transactions WHERE idempotency_key = ? LIMIT 1",
            (idempotency_key,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def account_balance(account_type: str, account_id: str, currency: str = "USD") -> float:
    """balance = SUM(amount) de movimientos posted (signed)."""
    ensure_init()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS bal
            FROM financial_transactions
            WHERE account_type = ? AND account_id = ? AND currency = ?
              AND status = 'posted'
            """,
            (account_type, account_id, currency),
        ).fetchone()
        return _money(row["bal"] if row else 0)
    finally:
        conn.close()


def post_entry(
    *,
    entry_type: str,
    account_type: str,
    account_id: str,
    amount: float,
    currency: str = "USD",
    reference: str = "",
    related_order: str = "",
    related_payment: str = "",
    idempotency_key: str,
    metadata: dict | None = None,
    status: str = "posted",
    allow_negative_balance: bool = False,
) -> dict[str, Any]:
    """
    Inserta un movimiento durable e idempotente.
    amount es signed: crédito > 0, débito < 0.
    Si idempotency_key ya existe, retorna el registro existente (no duplica dinero).
    """
    ensure_init()
    key = (idempotency_key or "").strip()
    if not key:
        raise ValueError("idempotency_key requerido")

    existing = get_by_idempotency(key)
    if existing:
        return existing

    amt = _money(amount)
    tx_id = uuid.uuid4().hex[:20]
    now = int(time.time() * 1000)
    meta = json.dumps(metadata or {}, ensure_ascii=False)

    with _tx() as conn:
        # Re-check inside lock/transaction
        row = conn.execute(
            "SELECT * FROM financial_transactions WHERE idempotency_key = ? LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            return dict(row)

        if amt < 0 and not allow_negative_balance:
            bal_row = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS bal
                FROM financial_transactions
                WHERE account_type = ? AND account_id = ? AND currency = ?
                  AND status = 'posted'
                """,
                (account_type, account_id, currency),
            ).fetchone()
            bal = _money(bal_row["bal"] if bal_row else 0)
            if bal + amt < -0.001:
                raise ValueError(
                    f"Saldo insuficiente en ledger ({account_type}:{account_id}={bal})"
                )

        conn.execute(
            """
            INSERT INTO financial_transactions (
                transaction_id, type, account_type, account_id, amount, currency,
                reference, related_order, related_payment, status, created_at,
                idempotency_key, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                entry_type,
                account_type,
                account_id,
                amt,
                currency.upper(),
                reference or "",
                related_order or "",
                related_payment or "",
                status,
                now,
                key,
                meta,
            ),
        )
        out = conn.execute(
            "SELECT * FROM financial_transactions WHERE transaction_id = ?",
            (tx_id,),
        ).fetchone()
        return dict(out)


def list_entries(
    account_type: str | None = None,
    account_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_init()
    conn = _connect()
    try:
        if account_type and account_id:
            rows = conn.execute(
                """
                SELECT * FROM financial_transactions
                WHERE account_type = ? AND account_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (account_type, account_id, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM financial_transactions ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def architecture_note() -> dict[str, str]:
    return {
        "source_of_truth": "SQLite financial_transactions (this module)",
        "event_bus": "Kafka topics (fact_* / market_*)",
        "analytics": "Apache Pinot realtime tables",
        "disclaimer": (
            "Platform transactional ledger — not a regulated bank ledger. "
            "Card data stays with PSP; this stores platform money movements only."
        ),
        "path": ledger_path(),
    }
