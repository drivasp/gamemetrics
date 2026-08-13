"""Cache de claims partner↔juego (pending/approved) para lag de Pinot."""
from __future__ import annotations

from typing import Any

# partner_game_id -> row
_BY_ID: dict[str, dict[str, Any]] = {}
# product_id -> approved row
_APPROVED_BY_PRODUCT: dict[str, dict[str, Any]] = {}


def cache_partner_game(row: dict[str, Any]) -> None:
    pgid = str(row.get("partner_game_id") or "")
    if not pgid:
        return
    _BY_ID[pgid] = row
    product_id = str(row.get("product_id") or "")
    status = str(row.get("submission_status") or "").lower()
    deleted = bool(row.get("deleted"))
    if not product_id:
        return
    if status == "approved" and not deleted:
        _APPROVED_BY_PRODUCT[product_id] = row
        return
    current = _APPROVED_BY_PRODUCT.get(product_id)
    if current and str(current.get("partner_game_id")) == pgid:
        _APPROVED_BY_PRODUCT.pop(product_id, None)


def get_approved_claim(product_id: str) -> dict[str, Any] | None:
    row = _APPROVED_BY_PRODUCT.get(product_id)
    if not row or row.get("deleted"):
        return None
    if str(row.get("submission_status") or "").lower() != "approved":
        return None
    return row


def list_cached_claims(status: str | None = None) -> list[dict[str, Any]]:
    out = []
    for row in _BY_ID.values():
        if row.get("deleted"):
            continue
        if status and str(row.get("submission_status") or "").lower() != status.lower():
            continue
        out.append(row)
    out.sort(key=lambda r: int(r.get("created_at") or 0), reverse=True)
    return out


def get_claim(partner_game_id: str) -> dict[str, Any] | None:
    return _BY_ID.get(partner_game_id)
