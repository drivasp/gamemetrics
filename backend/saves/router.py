"""Cloud saves — slots ligeros en MinIO + metadata Pinot."""
from __future__ import annotations

import json
import time
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.storage import delete_object, get_bytes, put_bytes, sha256_hex

router = APIRouter(prefix="/saves", tags=["saves"])

MAX_SAVE_BYTES = 256 * 1024
MAX_SLOT = 2


class SavePutDTO(BaseModel):
    slot: int = Field(default=0, ge=0, le=MAX_SLOT)
    data: dict[str, Any] = Field(default_factory=dict)
    label: str = ""


async def _owns(user_id: str, product_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return len(rows) > 0


def _save_id(user_id: str, product_id: str, slot: int) -> str:
    return f"{user_id}_{product_id}_s{slot}"


def _object_path(user_id: str, product_id: str, slot: int) -> str:
    return f"saves/{user_id}/{product_id}/slot_{slot}.json"


@router.get("/{product_id}")
async def list_saves(
    product_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")

    rows = await pinot_query(
        f"SELECT save_id, user_id, product_id, slot, object_path, checksum, size_bytes, "
        f"label, updated_at FROM fact_cloud_saves "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false LIMIT 10"
    )
    items = [
        {
            "save_id": r[0],
            "product_id": r[2],
            "slot": int(r[3] or 0),
            "object_path": r[4] or "",
            "checksum": r[5] or "",
            "size_bytes": int(r[6] or 0),
            "label": r[7] or "",
            "updated_at": str(r[8]),
        }
        for r in rows
    ]
    items.sort(key=lambda x: x["slot"])
    return {"items": items, "max_slot": MAX_SLOT}


@router.get("/{product_id}/{slot}")
async def get_save(
    product_id: str,
    slot: int,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")
    if slot < 0 or slot > MAX_SLOT:
        raise HTTPException(400, f"Slot inválido (0–{MAX_SLOT})")

    path = _object_path(user_id, product_id, slot)
    raw = get_bytes(path)
    meta_rows = await pinot_query(
        f"SELECT save_id, checksum, size_bytes, label, updated_at FROM fact_cloud_saves "
        f"WHERE save_id = '{esc(_save_id(user_id, product_id, slot))}' "
        f"AND deleted = false LIMIT 1"
    )
    if not raw and not meta_rows:
        raise HTTPException(404, "No hay guardado en este slot")

    payload: dict[str, Any] = {}
    if raw:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"raw": raw.decode("utf-8", errors="replace")}

    meta = meta_rows[0] if meta_rows else None
    return {
        "product_id": product_id,
        "slot": slot,
        "data": payload,
        "checksum": (meta[1] if meta else sha256_hex(raw or b"")) or "",
        "size_bytes": int(meta[2] or len(raw or b"")),
        "label": (meta[3] if meta else "") or "",
        "updated_at": str(meta[4]) if meta else "",
    }


@router.put("/{product_id}")
async def put_save(
    product_id: str,
    body: SavePutDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")

    raw = json.dumps(body.data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_SAVE_BYTES:
        raise HTTPException(413, f"Guardado demasiado grande (máx {MAX_SAVE_BYTES} bytes)")

    path = _object_path(user_id, product_id, body.slot)
    put_bytes(path, raw, content_type="application/json")
    checksum = sha256_hex(raw)
    now_ms = int(time.time() * 1000)
    save_id = _save_id(user_id, product_id, body.slot)
    label = (body.label or body.data.get("label") or f"Slot {body.slot}")[:80]
    await kafka_send("fact_cloud_saves", save_id, {
        "save_id": save_id,
        "user_id": user_id,
        "product_id": product_id,
        "slot": body.slot,
        "object_path": path,
        "checksum": checksum,
        "size_bytes": len(raw),
        "label": label,
        "updated_at": now_ms,
        "deleted": False,
    })
    return {
        "save_id": save_id,
        "slot": body.slot,
        "checksum": checksum,
        "size_bytes": len(raw),
        "label": label,
        "updated_at": str(now_ms),
        "message": "Guardado en la nube",
    }


@router.delete("/{product_id}/{slot}", status_code=200)
async def delete_save(
    product_id: str,
    slot: int,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")
    if slot < 0 or slot > MAX_SLOT:
        raise HTTPException(400, f"Slot inválido (0–{MAX_SLOT})")

    save_id = _save_id(user_id, product_id, slot)
    path = _object_path(user_id, product_id, slot)
    delete_object(path)
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_cloud_saves", save_id, {
        "save_id": save_id,
        "user_id": user_id,
        "product_id": product_id,
        "slot": slot,
        "object_path": path,
        "checksum": "",
        "size_bytes": 0,
        "label": "",
        "updated_at": now_ms,
        "deleted": True,
    })
    return {"message": "Guardado eliminado", "slot": slot}
