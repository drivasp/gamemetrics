"""Middleware: rate limit por IP en endpoints financieros sensibles."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_IP: dict[str, deque[float]] = defaultdict(deque)

SENSITIVE_PREFIXES = (
    "/checkout",
    "/refunds",
    "/wallet",
    "/marketplace",
    "/admin/payouts",
    "/admin/chargebacks",
)


class FinancialRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 120, window_s: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window_s = window_s

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in SENSITIVE_PREFIXES) and request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            ip = request.client.host if request.client else "unknown"
            key = f"{ip}:{path.split('/')[1] if path.count('/') else path}"
            now = time.time()
            q = _IP[key]
            while q and now - q[0] > self.window_s:
                q.popleft()
            if len(q) >= self.limit:
                return JSONResponse(
                    {"detail": "Too many requests (financial rate limit)"},
                    status_code=429,
                )
            q.append(now)
        return await call_next(request)
