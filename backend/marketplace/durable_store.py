"""
Marketplace ownership durable (SQLite) — no solo memoria de proceso.

Dinero sigue en ledger.sqlite_store; aquí items/listings/txs/idempotency.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ledger.sqlite_store import ledger_path

_LOCK = threading.RLock()
_INITIALIZED = False


def _db_path() -> str:
    # Mismo directorio que el ledger financiero
    return str(Path(ledger_path()).parent / "marketplace.sqlite3")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_marketplace_store() -> None:
    global _INITIALIZED
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS market_items (
                    item_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_listings (
                    listing_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_txs (
                    tx_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_idempotency (
                    idem_key TEXT PRIMARY KEY,
                    tx_id TEXT NOT NULL
                );
                """
            )
            conn.commit()
        finally:
            conn.close()
        _INITIALIZED = True


def ensure_init() -> None:
    if not _INITIALIZED:
        init_marketplace_store()


def save_item(row: dict[str, Any]) -> None:
    ensure_init()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO market_items (item_id, payload_json) VALUES (?, ?)",
                (row["item_id"], json.dumps(row, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()


def get_item(item_id: str) -> dict[str, Any] | None:
    ensure_init()
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT payload_json FROM market_items WHERE item_id = ?", (item_id,)
        ).fetchone()
        return json.loads(r["payload_json"]) if r else None
    finally:
        conn.close()


def all_items() -> list[dict[str, Any]]:
    ensure_init()
    conn = _connect()
    try:
        rows = conn.execute("SELECT payload_json FROM market_items").fetchall()
        return [json.loads(r["payload_json"]) for r in rows]
    finally:
        conn.close()


def save_listing(row: dict[str, Any]) -> None:
    ensure_init()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO market_listings (listing_id, payload_json) VALUES (?, ?)",
                (row["listing_id"], json.dumps(row, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()


def get_listing(listing_id: str) -> dict[str, Any] | None:
    ensure_init()
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT payload_json FROM market_listings WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        return json.loads(r["payload_json"]) if r else None
    finally:
        conn.close()


def all_listings() -> list[dict[str, Any]]:
    ensure_init()
    conn = _connect()
    try:
        rows = conn.execute("SELECT payload_json FROM market_listings").fetchall()
        return [json.loads(r["payload_json"]) for r in rows]
    finally:
        conn.close()


def save_tx(row: dict[str, Any]) -> None:
    ensure_init()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO market_txs (tx_id, payload_json) VALUES (?, ?)",
                (row["tx_id"], json.dumps(row, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()


def get_tx(tx_id: str) -> dict[str, Any] | None:
    ensure_init()
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT payload_json FROM market_txs WHERE tx_id = ?", (tx_id,)
        ).fetchone()
        return json.loads(r["payload_json"]) if r else None
    finally:
        conn.close()


def all_txs() -> list[dict[str, Any]]:
    ensure_init()
    conn = _connect()
    try:
        rows = conn.execute("SELECT payload_json FROM market_txs").fetchall()
        return [json.loads(r["payload_json"]) for r in rows]
    finally:
        conn.close()


def get_idempotency(key: str) -> str | None:
    ensure_init()
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT tx_id FROM market_idempotency WHERE idem_key = ?", (key,)
        ).fetchone()
        return r["tx_id"] if r else None
    finally:
        conn.close()


def set_idempotency(key: str, tx_id: str) -> None:
    ensure_init()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO market_idempotency (idem_key, tx_id) VALUES (?, ?)",
                (key, tx_id),
            )
            conn.commit()
        finally:
            conn.close()
