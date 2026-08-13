"""Rate limiting in-memory (process-local). Production: Redis — OPEN_DEPENDENCY."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


async def rate_limit(user_id: str, action: str, *, limit: int, window_s: int) -> None:
    key = f"{user_id}:{action}"
    now = time.time()
    q = _BUCKETS[key]
    while q and now - q[0] > window_s:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            429,
            f"Rate limit: máx {limit} {action} por {window_s}s",
        )
    q.append(now)


def middleware_client_key(ip: str, path: str) -> str:
    return f"ip:{ip}:{path}"
