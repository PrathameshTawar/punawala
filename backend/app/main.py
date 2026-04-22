import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from dotenv import load_dotenv
from app.config import settings
from app.database import init_db, get_db, async_session_factory, User
from app.auth import hash_password
from app.middleware import RequestTracingMiddleware, RateLimitMiddleware
from app.routes.auth         import router as auth_router
from app.routes.kyc          import router as kyc_router
from app.routes.auditor      import router as auditor_router
from app.routes.applications import router as apps_router
from app.routes.audit        import router as audit_router
from app.schemas import HealthResponse

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
try:
    import structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
            if settings.ENVIRONMENT == "development"
            else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger("main")
except ImportError:
    logging.basicConfig(
        level=logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.ENVIRONMENT == "development":
        await _seed_demo_users()
    # Use stdlib-compatible log call so both structlog and logging work
    logging.getLogger("main").info(
        f"startup_complete version=3.0.0 env={settings.ENVIRONMENT}"
    )
    yield


app = FastAPI(
    title="Loan Wizard — KYC Platform",
    version="3.0.0",
    description="AI-assisted video KYC with deterministic risk engine and full auditability",
    lifespan=lifespan,
)

# OTel — optional, placed after app is defined so FastAPIInstrumentor can reference it
if settings.OTEL_SERVICE_NAME:
    try:
        from opentelemetry import trace  # type: ignore[import]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import]
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore[import]
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore[import]
        trace.set_tracer_provider(TracerProvider())
        trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        FastAPIInstrumentor().instrument_app(app)
    except ImportError:
        logging.getLogger("main").warning("otel_packages_not_installed — skipping instrumentation")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

PREFIX = "/api/v1"
app.include_router(auth_router,     prefix=PREFIX)
app.include_router(kyc_router,      prefix=PREFIX)
app.include_router(auditor_router,  prefix=PREFIX)
app.include_router(apps_router,     prefix=PREFIX)
app.include_router(audit_router,    prefix=PREFIX)


@app.get("/health", response_model=HealthResponse)
async def health() -> JSONResponse:
    """
    Real dependency health check.
    Returns 200 when all dependencies are healthy.
    Returns 503 when degraded — K8s liveness probes and load balancers use this.
    """
    from sqlalchemy import text
    checks = HealthResponse(
        status="ok",
        version="3.0.0",
        environment=settings.ENVIRONMENT,
        database="unknown",
    )

    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks.database = "ok"
    except Exception as e:
        checks.database = f"error: {e}"
        checks.status   = "degraded"

    if settings.REDIS_URL:
        try:
            import redis  # type: ignore[import]
            r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            r.ping()
            checks.redis = "ok"
        except Exception as e:
            checks.redis  = f"error: {e}"
            checks.status = "degraded"

    status_code = 200 if checks.status == "ok" else 503
    return JSONResponse(content=checks.model_dump(), status_code=status_code)


@app.get("/metrics")
def metrics():
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST  # type: ignore[import]
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return {"error": "prometheus_client not installed"}


async def _seed_demo_users() -> None:
    from sqlalchemy import select
    async with async_session_factory() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar():
            return
        db.add_all([
            User(username="applicant", hashed_password=hash_password("Demo@12345"),
                 role="applicant", full_name="Demo Applicant"),
            User(username="auditor",   hashed_password=hash_password("Demo@12345"),
                 role="auditor",   full_name="Bank Auditor"),
            User(username="admin",     hashed_password=hash_password("Demo@12345"),
                 role="admin",     full_name="System Admin"),
        ])
        await db.commit()
        logging.getLogger("main").info("demo_users_seeded")
