"""
Marketplace P2P — listing / buy / fee / ownership (sandbox wallet).

Ownership/listings/txs: SQLite durable_store.
Dinero: ledger SQLite vía wallet.apply_transaction.
Kafka: event bus analytics.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from checkout.financial_audit import audit_event
from marketplace import durable_store as store
from marketplace.fees_calc import GAME_FEE_PCT, PLATFORM_FEE_PCT, _money, fee_breakdown
from shared.kafka_producer import kafka_send
from wallet.servicio import apply_transaction, get_balance

store.ensure_init()


async def mint_item(
    *,
    owner_user_id: str,
    game_id: str,
    item_name: str,
    item_type: str = "cosmetic",
) -> dict[str, Any]:
    item_id = uuid.uuid4().hex[:16]
    now = int(time.time() * 1000)
    row = {
        "item_id": item_id,
        "owner_user_id": owner_user_id,
        "game_id": game_id,
        "item_name": item_name,
        "item_type": item_type,
        "status": "owned",
        "created_at": now,
        "updated_at": now,
        "deleted": False,
    }
    store.save_item(row)
    await kafka_send("market_items", item_id, row)
    return row


async def create_listing(
    *,
    seller_user_id: str,
    item_id: str,
    price_usd: float,
) -> dict[str, Any]:
    item = store.get_item(item_id)
    if not item or item.get("deleted"):
        raise ValueError("Item no encontrado")
    if item["owner_user_id"] != seller_user_id:
        raise ValueError("No eres el dueño del item")
    if item["status"] != "owned":
        raise ValueError("El item no está disponible para listar")
    price = _money(price_usd)
    if price <= 0:
        raise ValueError("Precio inválido")

    listing_id = uuid.uuid4().hex[:16]
    now = int(time.time() * 1000)
    fees = fee_breakdown(price)
    listing = {
        "listing_id": listing_id,
        "item_id": item_id,
        "seller_user_id": seller_user_id,
        "game_id": item["game_id"],
        "item_name": item["item_name"],
        "price_usd": price,
        "currency": "USD",
        "status": "active",
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "game_fee_pct": GAME_FEE_PCT,
        "created_at": now,
        "updated_at": now,
        "deleted": False,
        "fee_preview": fees,
    }
    item["status"] = "listed"
    item["updated_at"] = now
    store.save_listing(listing)
    store.save_item(item)
    await kafka_send("market_listings", listing_id, listing)
    await kafka_send("market_items", item_id, item)
    audit_event(
        actor_id=seller_user_id,
        action="market_create_listing",
        entity_type="market_listing",
        entity_id=listing_id,
        amount=price,
        after=listing,
    )
    return listing


async def cancel_listing(*, seller_user_id: str, listing_id: str) -> dict[str, Any]:
    listing = store.get_listing(listing_id)
    if not listing or listing.get("deleted"):
        raise ValueError("Listing no encontrado")
    if listing["seller_user_id"] != seller_user_id:
        raise ValueError("No eres el vendedor")
    if listing["status"] != "active":
        raise ValueError("Listing no activo")
    now = int(time.time() * 1000)
    listing["status"] = "cancelled"
    listing["updated_at"] = now
    item = store.get_item(listing["item_id"])
    if item:
        item["status"] = "owned"
        item["updated_at"] = now
        store.save_item(item)
        await kafka_send("market_items", item["item_id"], item)
    store.save_listing(listing)
    await kafka_send("market_listings", listing_id, listing)
    return listing


async def purchase_listing(
    *,
    buyer_user_id: str,
    listing_id: str,
    idempotency_key: str = "",
) -> dict[str, Any]:
    key = (idempotency_key or "").strip() or f"mktbuy_{buyer_user_id}_{listing_id}"
    existing_tx_id = store.get_idempotency(key)
    if existing_tx_id:
        tx = store.get_tx(existing_tx_id)
        if tx:
            return tx

    prior_buyer = None
    try:
        from ledger.sqlite_store import get_by_idempotency

        prior_buyer = get_by_idempotency(f"mkt_buyer_{listing_id}_{key}")
    except Exception:
        pass
    if prior_buyer:
        for tx in store.all_txs():
            if tx.get("idempotency_key") == key:
                store.set_idempotency(key, tx["tx_id"])
                return tx

    listing = store.get_listing(listing_id)
    if not listing or listing.get("deleted"):
        raise ValueError("Listing no encontrado")
    if listing["status"] != "active":
        raise ValueError("Listing no disponible")
    if listing["seller_user_id"] == buyer_user_id:
        raise ValueError("No puedes comprar tu propio listing")

    item = store.get_item(listing["item_id"])
    if not item or item["status"] != "listed":
        raise ValueError("Item no listado")

    fees = fee_breakdown(float(listing["price_usd"]))
    bal = await get_balance(buyer_user_id)
    if bal + 0.001 < fees["gross"]:
        raise ValueError(f"Saldo insuficiente (${bal:.2f})")

    await apply_transaction(
        buyer_user_id,
        -fees["gross"],
        tx_type="purchase",
        reference_id=listing_id,
        idempotency_key=f"mkt_buyer_{listing_id}_{key}",
    )
    await apply_transaction(
        listing["seller_user_id"],
        fees["seller_net"],
        tx_type="credit",
        reference_id=listing_id,
        idempotency_key=f"mkt_seller_{listing_id}_{key}",
    )
    try:
        from ledger.sqlite_store import post_entry

        if fees["platform_fee"] > 0:
            post_entry(
                entry_type="marketplace_platform_fee",
                account_type="platform",
                account_id="gamemetrics",
                amount=fees["platform_fee"],
                reference=listing_id,
                related_order=listing_id,
                idempotency_key=f"mkt_platfee_{listing_id}_{key}",
                metadata={"listing_id": listing_id, "buyer": buyer_user_id},
                allow_negative_balance=True,
            )
        if fees["game_fee"] > 0:
            post_entry(
                entry_type="marketplace_game_fee",
                account_type="platform",
                account_id="gamemetrics",
                amount=fees["game_fee"],
                reference=listing_id,
                related_order=listing_id,
                idempotency_key=f"mkt_gamefee_{listing_id}_{key}",
                metadata={"listing_id": listing_id, "game_id": listing["game_id"]},
                allow_negative_balance=True,
            )
    except Exception as exc:
        print(f"[marketplace] durable fee ledger skip: {exc}")

    now = int(time.time() * 1000)
    tx_id = uuid.uuid4().hex[:16]
    item["owner_user_id"] = buyer_user_id
    item["status"] = "owned"
    item["updated_at"] = now
    listing["status"] = "sold"
    listing["updated_at"] = now

    tx = {
        "tx_id": tx_id,
        "listing_id": listing_id,
        "item_id": item["item_id"],
        "buyer_user_id": buyer_user_id,
        "seller_user_id": listing["seller_user_id"],
        "game_id": listing["game_id"],
        "item_name": listing["item_name"],
        "gross_amount": fees["gross"],
        "platform_fee": fees["platform_fee"],
        "game_fee": fees["game_fee"],
        "seller_net": fees["seller_net"],
        "currency": "USD",
        "status": "completed",
        "idempotency_key": key,
        "created_at": now,
        "deleted": False,
    }
    store.save_tx(tx)
    store.set_idempotency(key, tx_id)
    store.save_listing(listing)
    store.save_item(item)

    await kafka_send("market_transactions", tx_id, tx)
    await kafka_send("market_listings", listing_id, listing)
    await kafka_send("market_items", item["item_id"], item)

    audit_event(
        actor_id=buyer_user_id,
        action="market_purchase",
        entity_type="market_transaction",
        entity_id=tx_id,
        amount=fees["gross"],
        after=tx,
    )
    return tx


def list_active_listings(limit: int = 50) -> list[dict[str, Any]]:
    items = [
        l
        for l in store.all_listings()
        if l.get("status") == "active" and not l.get("deleted")
    ]
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:limit]


def inventory_for_user(user_id: str) -> list[dict[str, Any]]:
    return [
        i
        for i in store.all_items()
        if i.get("owner_user_id") == user_id and not i.get("deleted")
    ]


def history_for_user(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    txs = [
        t
        for t in store.all_txs()
        if t.get("buyer_user_id") == user_id or t.get("seller_user_id") == user_id
    ]
    txs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return txs[:limit]


def seller_balance_from_market(user_id: str) -> float:
    return _money(
        sum(
            float(t.get("seller_net") or 0)
            for t in store.all_txs()
            if t.get("seller_user_id") == user_id and t.get("status") == "completed"
        )
    )
