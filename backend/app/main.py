"""AEROGRID — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import AppError, app_error_handler, correlation_id_middleware, make_error_response
from app.api.observability import metrics, observability_middleware
from app.api.rate_limit import rate_limit_middleware
from app.api.routers import analytics, calibration, health, notifications, observations, signals
from app.application.correlate_observation import CorrelateObservationUseCase
from app.application.interpret_observation import InterpretObservationUseCase
from app.application.submit_observation import SubmitObservationUseCase
from app.config.settings import settings
from app.domain.policies import CorrelationConfig
from app.infrastructure.db import async_session_factory, init_db
from app.infrastructure.gemini_interpreter import GeminiInterpreterAdapter
from app.infrastructure.repositories import (
    InMemoryEventBus,
    SQLAlchemyAuditLog,
    SQLAlchemyInterpretationStore,
    SQLAlchemyObservationStore,
    SQLAlchemySignalEventStore,
    SQLAlchemySignalStore,
)


async def generic_error_handler(request, exc):
    correlation_id = getattr(request.state, "correlation_id", "")
    return make_error_response(
        code="INTERNAL_ERROR",
        message="Internal server error",
        status_code=500,
        correlation_id=correlation_id,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # C1 FIX: Session stays open for the lifetime of the application.
    # Each request creates its own session via get_db_session dependency.
    session = async_session_factory()
    try:
        config = CorrelationConfig(
            threshold_watch=settings.threshold_watch,
            threshold_probable_hotspot=settings.threshold_probable_hotspot,
            threshold_high_confidence=settings.threshold_high_confidence,
            min_observations_watch=settings.min_observations_watch,
            min_observations_probable_hotspot=settings.min_observations_probable_hotspot,
            min_observations_high_confidence=settings.min_observations_high_confidence,
            min_source_types_probable_hotspot=settings.min_source_types_probable_hotspot,
            min_source_types_high_confidence=settings.min_source_types_high_confidence,
        )

        obs_store = SQLAlchemyObservationStore(session)
        interp_store = SQLAlchemyInterpretationStore(session)
        signal_store = SQLAlchemySignalStore(session)
        signal_event_store = SQLAlchemySignalEventStore(session)
        audit_log = SQLAlchemyAuditLog(session)
        interpreter = GeminiInterpreterAdapter()
        event_bus = InMemoryEventBus()

        # Rate limiter
        from app.infrastructure.rate_limiter import InMemoryRateLimiter
        rate_limiter = InMemoryRateLimiter()
        app.state.rate_limiter = rate_limiter

        # Notification system
        from app.infrastructure.notifications import (
            EmailNotificationService,
            InAppNotificationService,
            NotificationOrchestrator,
        )
        email_service = EmailNotificationService()
        in_app_service = InAppNotificationService(event_bus)
        notification_orchestrator = NotificationOrchestrator(email_service, in_app_service)

        app.state.submit_observation_uc = SubmitObservationUseCase(
            obs_store, audit_log, event_bus
        )
        app.state.interpret_observation_uc = InterpretObservationUseCase(
            obs_store, interp_store, interpreter, audit_log, event_bus
        )
        app.state.correlate_observation_uc = CorrelateObservationUseCase(
            signal_store, signal_event_store, event_bus, config
        )
        app.state.notification_orchestrator = notification_orchestrator
        app.state.db_session = session

        yield
    finally:
        await session.close()


app = FastAPI(
    title="AEROGRID",
    description="AI-Powered Hyperlocal Environmental Intelligence Platform",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.middleware("http")(correlation_id_middleware)
app.middleware("http")(observability_middleware)


# Rate limiting middleware
@app.middleware("http")
async def rate_limiting(request: Request, call_next):
    return await rate_limit_middleware(request, call_next, request.app.state.rate_limiter)


# Authentication middleware — API key check for non-exempt paths
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    exempt = [p.strip() for p in settings.auth_exempt_paths.split(",")]

    # Skip auth for exempt paths and OpenAPI docs
    if any(path.startswith(e) for e in exempt) or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing API key"}},
        )

    return await call_next(request)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, generic_error_handler)


@app.get("/api/v1/metrics/live")
async def live_metrics():
    """Real-time operational metrics — not the static /metrics endpoint."""
    from fastapi.responses import JSONResponse
    return JSONResponse(content=metrics.get_summary())

app.include_router(observations.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(calibration.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
