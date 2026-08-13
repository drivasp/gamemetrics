"""
Marketplace P2P — listing / buy / fee / ownership (sandbox wallet).

Pago vía wallet sandbox. PSP real = OPEN_DEPENDENCY (Stripe).
Fee política: MARKETPLACE_PLATFORM_FEE_PCT + MARKETPLACE_GAME_FEE_PCT (defaults 5+10).
"""
from __future__ import annotations

import os
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from checkout.financial_audit import audit_event
from shared.kafka_producer import kafka_send
from wallet.servicio import apply_transaction, get_balance

PLATFORM_FEE_PCT = float(os.getenv("MARKETPLACE_PLATFORM_FEE_PCT", "5"))
GAME_FEE_PCT = float(os.getenv("MARKETPLACE_GAME_FEE_PCT", "10"))

_ITEMS: dict[str, dict[str, Any]] = {}  # item_id -> ownership
_LISTINGS: dict[str, dict[str, Any]] = {}
_TXS: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY: dict[str, str] = {}  # key -> tx_id


def _money(v: float) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def fee_breakdown(price: float) -> dict[str, float]:
    gross = _money(price)
    platform = _money(gross * PLATFORM_FEE_PCT / 100.0)
    game = _money(gross * GAME_FEE_PCT / 100.0)
    seller = _money(gross - platform - game)
    return {
        "gross": gross,
        "platform_fee": platform,
        "game_fee": game,
        "seller_net": seller,
        "total_fee_pct": PLATFORM_FEE_PCT + GAME_FEE_PCT,
    }


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
        "status": "owned",  # owned | listed | traded
        "created_at": now,
        "updated_at": now,
        "deleted": False,
    }
    _ITEMS[item_id] = row
    await kafka_send("market_items", item_id, row)
    return row


async def create_listing(
    *,
    seller_user_id: str,
    item_id: str,
    price_usd: float,
) -> dict[str, Any]:
    item = _ITEMS.get(item_id)
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
        "status": "active",  # active | sold | cancelled
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "game_fee_pct": GAME_FEE_PCT,
        "created_at": now,
        "updated_at": now,
        "deleted": False,
        "fee_preview": fees,
    }
    item["status"] = "listed"
    item["updated_at"] = now
    _LISTINGS[listing_id] = listing
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
    listing = _LISTINGS.get(listing_id)
    if not listing or listing.get("deleted"):
        raise ValueError("Listing no encontrado")
    if listing["seller_user_id"] != seller_user_id:
        raise ValueError("No eres el vendedor")
    if listing["status"] != "active":
        raise ValueError("Listing no activo")
    now = int(time.time() * 1000)
    listing["status"] = "cancelled"
    listing["updated_at"] = now
    item = _ITEMS.get(listing["item_id"])
    if item:
        item["status"] = "owned"
        item["updated_at"] = now
        await kafka_send("market_items", item["item_id"], item)
    await kafka_send("market_listings", listing_id, listing)
    return listing


async def purchase_listing(
    *,
    buyer_user_id: str,
    listing_id: str,
    idempotency_key: str = "",
) -> dict[str, Any]:
    key = (idempotency_key or "").strip() or f"mktbuy_{buyer_user_id}_{listing_id}"
    if key in _IDEMPOTENCY:
        tx_id = _IDEMPOTENCY[key]
        return _TXS[tx_id]

    listing = _LISTINGS.get(listing_id)
    if not listing or listing.get("deleted"):
        raise ValueError("Listing no encontrado")
    if listing["status"] != "active":
        raise ValueError("Listing no disponible")
    if listing["seller_user_id"] == buyer_user_id:
        raise ValueError("No puedes comprar tu propio listing")

    item = _ITEMS.get(listing["item_id"])
    if not item or item["status"] != "listed":
        raise ValueError("Item no listado")

    fees = fee_breakdown(float(listing["price_usd"]))
    bal = await get_balance(buyer_user_id)
    if bal + 0.001 < fees["gross"]:
        raise ValueError(f"Saldo insuficiente (${bal:.2f})")

    # Debit buyer
    await apply_transaction(
        buyer_user_id,
        -fees["gross"],
        tx_type="purchase",
        reference_id=listing_id,
        idempotency_key=f"mkt_buyer_{key}",
    )
    # Credit seller net
    await apply_transaction(
        listing["seller_user_id"],
        fees["seller_net"],
        tx_type="credit",
        reference_id=listing_id,
        idempotency_key=f"mkt_seller_{key}",
    )

    now = int(time.time() * 1000)
    tx_id = uuid.uuid4().hex[:16]
    # Transfer ownership
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
    _TXS[tx_id] = tx
    _IDEMPOTENCY[key] = tx_id
    _LISTINGS[listing_id] = listing
    _ITEMS[item["item_id"]] = item

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
    items = [l for l in _LISTINGS.values() if l.get("status") == "active" and not l.get("deleted")]
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:limit]


def inventory_for_user(user_id: str) -> list[dict[str, Any]]:
    return [
        i for i in _ITEMS.values()
        if i.get("owner_user_id") == user_id and not i.get("deleted")
    ]


def history_for_user(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    txs = [
        t for t in _TXS.values()
        if t.get("buyer_user_id") == user_id or t.get("seller_user_id") == user_id
    ]
    txs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return txs[:limit]


def seller_balance_from_market(user_id: str) -> float:
    return _money(sum(
        float(t.get("seller_net") or 0)
        for t in _TXS.values()
        if t.get("seller_user_id") == user_id and t.get("status") == "completed"
    ))
