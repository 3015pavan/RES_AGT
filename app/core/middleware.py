from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import error_envelope
from app.core.metrics import metrics_store
from app.core.request_context import request_id_ctx

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        duration = time.perf_counter() - start
        response.headers["x-request-id"] = request_id
        metrics_store.observe_request(response.status_code, duration)
        logger.info(
            "request_completed method=%s path=%s status=%s duration_seconds=%.6f client=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            request.client.host if request.client else "unknown",
        )
        return response


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("x-api-key") or request.client.host if request.client else "anonymous"
        if not self.limiter.allow(key):
            request_id = getattr(request.state, "request_id", None)
            return JSONResponse(
                status_code=429,
                content=error_envelope(
                    code="RATE_LIMIT_EXCEEDED",
                    message="Too many requests",
                    request_id=request_id,
                ),
            )
        return await call_next(request)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_request_mb: int):
        super().__init__(app)
        self.max_request_bytes = max_request_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_request_bytes:
                    request_id = getattr(request.state, "request_id", None)
                    return JSONResponse(
                        status_code=413,
                        content=error_envelope(
                            code="REQUEST_TOO_LARGE",
                            message=f"Request body exceeds {self.max_request_bytes} bytes",
                            request_id=request_id,
                        ),
                    )
            except ValueError:
                request_id = getattr(request.state, "request_id", None)
                return JSONResponse(
                    status_code=400,
                    content=error_envelope(
                        code="INVALID_CONTENT_LENGTH",
                        message="Invalid content-length header",
                        request_id=request_id,
                    ),
                )

        return await call_next(request)
