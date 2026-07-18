"""Structured error handling and correlation ID middleware."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorBody, ErrorResponse


def make_error_response(
    code: str,
    message: str,
    status_code: int = 400,
    correlation_id: str = "",
    details: list[dict] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or [],
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id

    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - start) * 1000

    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

    return response


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: list[dict] | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "")
    return make_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        correlation_id=correlation_id,
        details=exc.details,
    )
