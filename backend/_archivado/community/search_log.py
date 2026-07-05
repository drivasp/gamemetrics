"""Log de búsquedas (analytics)."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from shared.auth_deps import require_token
from shared.kafka_producer import kafka_send

router = APIRouter(prefix="/search", tags=["search"])


class SearchLogDTO(BaseModel):
    query_text: str = Field(min_length=1, max_length=200)
    results_count: int = Field(default=0, ge=0)


@router.post("/log", status_code=201)
async def log_search(
    body: SearchLogDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    user_id = ""
    if authorization:
        try:
            _, user_id = require_token(authorization)
        except Exception:
            user_id = ""
    qid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_search_queries", qid, {
        "query_id": qid,
        "user_id": user_id or "anonymous",
        "query_text": body.query_text.strip()[:200],
        "results_count": int(body.results_count),
        "created_at": now_ms,
        "deleted": False,
    })
    return {"query_id": qid, "status": "ok"}
