from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import metrics_store
from app.core.middleware import RateLimiter, RateLimitMiddleware, RequestContextMiddleware, RequestSizeMiddleware
from app.core.startup import ReadinessState, run_startup_checks

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Unified Agentic AI Backend",
    version="0.1.0",
    description=(
        "Grounded agentic AI backend. Responses are generated only from Supabase SQL and pgvector retrievals. "
        "If no data is found, responses return exactly NO DATA AVAILABLE."
    ),
    openapi_tags=[
        {"name": "ingestion", "description": "Upload and email ingestion flows"},
        {"name": "query", "description": "Grounded chat and report generation"},
        {"name": "catalog", "description": "Read-only listings for stored data"},
        {"name": "ops", "description": "Health, readiness, and metrics"},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestSizeMiddleware, max_request_mb=settings.max_request_mb)
app.add_middleware(
    RateLimitMiddleware,
    limiter=RateLimiter(max_requests=settings.rate_limit_per_minute, window_seconds=60),
)
app.include_router(router)
register_exception_handlers(app)

readiness_state = ReadinessState(ready=False, reason="startup not executed")


@app.on_event("startup")
async def on_startup() -> None:
    global readiness_state
    readiness_state = run_startup_checks(settings)


@app.get("/health", tags=["ops"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["ops"], summary="Readiness check with migration guard")
def ready() -> dict[str, str | bool]:
    return {"ready": readiness_state.ready, "reason": readiness_state.reason}


@app.get("/metrics", tags=["ops"], summary="In-process service metrics")
def metrics() -> dict[str, object]:
    return metrics_store.snapshot()
