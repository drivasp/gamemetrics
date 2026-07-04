import json
import math
import time
import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

router = APIRouter()

VALID_COLLECTIONS = {
    "plataformas", "generos", "clasificaciones_esrb", "desarrolladores",
    "publicadores", "empleados", "contratos", "catalogo_distribucion",
    "campanas_marketing", "evaluaciones_analiticas",
}


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


def _new_id() -> str:
    return uuid.uuid4().hex[:15]


def _row_to_item(row: list) -> dict:
    record_id, data_json, created_at = row[0], row[1], row[2]
    try:
        data = json.loads(data_json)
    except Exception:
        data = {}
    return {"id": record_id, "created_at": created_at, **data}


@router.get("/{collection}/records")
async def list_records(
    collection: str,
    page: int = Query(1, ge=1),
    perPage: int = Query(15, ge=1, le=200),
):
    if collection not in VALID_COLLECTIONS:
        raise HTTPException(404, "Colección no encontrada")

    offset = (page - 1) * perPage
    col = _esc(collection)

    count_rows = await pinot_query(
        f"SELECT COUNT(*) FROM emp_records WHERE collection = '{col}' AND deleted = FALSE"
    )
    total = int(count_rows[0][0]) if count_rows else 0

    rows = await pinot_query(
        f"SELECT record_id, data_json, created_at FROM emp_records "
        f"WHERE collection = '{col}' AND deleted = FALSE "
        f"ORDER BY created_at DESC LIMIT {perPage} OFFSET {offset}"
    )

    items = [_row_to_item(r) for r in rows]
    return {
        "items": items,
        "totalItems": total,
        "totalPages": max(1, math.ceil(total / perPage)),
        "page": page,
        "perPage": perPage,
    }


@router.post("/{collection}/records", status_code=201)
async def create_record(collection: str, body: dict):
    if collection not in VALID_COLLECTIONS:
        raise HTTPException(404, "Colección no encontrada")

    record_id = _new_id()
    now_ms = int(time.time() * 1000)

    await kafka_send("emp_records", record_id, {
        "record_id": record_id,
        "collection": collection,
        "data_json": json.dumps(body, default=str),
        "deleted": False,
        "created_at": now_ms,
    })

    return {"id": record_id, "created_at": now_ms, **body}


@router.patch("/{collection}/records/{record_id}")
async def update_record(collection: str, record_id: str, body: dict):
    if collection not in VALID_COLLECTIONS:
        raise HTTPException(404, "Colección no encontrada")

    rows = await pinot_query(
        f"SELECT record_id, data_json, created_at FROM emp_records "
        f"WHERE record_id = '{_esc(record_id)}' AND deleted = FALSE LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Registro no encontrado")

    existing_data = {}
    original_created_at = rows[0][2]
    try:
        existing_data = json.loads(rows[0][1])
    except Exception:
        pass

    merged = {**existing_data, **body}

    await kafka_send("emp_records", record_id, {
        "record_id": record_id,
        "collection": collection,
        "data_json": json.dumps(merged, default=str),
        "deleted": False,
        "created_at": original_created_at,
    })

    return {"id": record_id, "created_at": original_created_at, **merged}


@router.delete("/{collection}/records/{record_id}", status_code=204)
async def delete_record(collection: str, record_id: str):
    if collection not in VALID_COLLECTIONS:
        raise HTTPException(404, "Colección no encontrada")

    await kafka_send("emp_records", record_id, {
        "record_id": record_id,
        "collection": collection,
        "data_json": "{}",
        "deleted": True,
        "created_at": int(time.time() * 1000),
    })

    return Response(status_code=204)
