"""Observability — Structured logging, metrics, and tracing.

Every request gets: Request ID, Correlation ID, Timestamp, Response Time.
Metrics are exposed via the /metrics endpoint.
Traces propagate across Frontend → API → Gemini → Correlation → Database.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request

# Structured logger — every log entry is a JSON object
logger = logging.getLogger("aerogrid")
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter(
        '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
    )
)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# --- Metrics Store (in-memory, resets on restart) ---

class MetricsStore:
    def __init__(self) -> None:
        self.observations_submitted = 0
        self.signals_created = 0
        self.gemini_latency_ms: list[float] = []
        self.provider_failures: dict[str, int] = {}
        self.api_latencies_ms: list[float] = []
        self.request_count = 0
        self.error_count = 0
        self.start_time = datetime.now(timezone.utc)

    def record_observation(self) -> None:
        self.observations_submitted += 1

    def record_signal(self) -> None:
        self.signals_created += 1

    def record_gemini_latency(self, ms: float) -> None:
        self.gemini_latency_ms.append(ms)
        if len(self.gemini_latency_ms) > 1000:
            self.gemini_latency_ms = self.gemini_latency_ms[-500:]

    def record_provider_failure(self, provider: str) -> None:
        self.provider_failures[provider] = self.provider_failures.get(provider, 0) + 1

    def record_api_latency(self, ms: float) -> None:
        self.api_latencies_ms.append(ms)
        if len(self.api_latencies_ms) > 1000:
            self.api_latencies_ms = self.api_latencies_ms[-500:]

    def record_request(self, is_error: bool = False) -> None:
        self.request_count += 1
        if is_error:
            self.error_count += 1

    def get_summary(self) -> dict:
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        avg_gemini = (
            sum(self.gemini_latency_ms) / len(self.gemini_latency_ms)
            if self.gemini_latency_ms else 0
        )
        avg_api = (
            sum(self.api_latencies_ms) / len(self.api_latencies_ms)
            if self.api_latencies_ms else 0
        )
        p95_api = sorted(self.api_latencies_ms)[int(len(self.api_latencies_ms) * 0.95)] if self.api_latencies_ms else 0
        return {
            "observations_submitted": self.observations_submitted,
            "signals_created": self.signals_created,
            "gemini_avg_latency_ms": round(avg_gemini, 1),
            "provider_failures": dict(self.provider_failures),
            "api_avg_latency_ms": round(avg_api, 1),
            "api_p95_latency_ms": round(p95_api, 1),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.request_count, 1) * 100, 2),
            "uptime_seconds": round(uptime, 1),
        }


# Global metrics store
metrics = MetricsStore()


# --- Middleware ---

async def observability_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4())[:8])

    start = time.monotonic()
    response = None
    is_error = False

    try:
        response = await call_next(request)
        if response.status_code >= 400:
            is_error = True
    except Exception:
        is_error = True
        raise
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000
        metrics.record_api_latency(elapsed_ms)
        metrics.record_request(is_error)

        logger.info(
            f"{request.method} {request.url.path} "
            f"status={getattr(response, 'status_code', 500)} "
            f"latency={elapsed_ms:.1f}ms "
            f"request_id={request_id} "
            f"correlation_id={correlation_id}"
        )

    if response:
        response.headers["X-Request-ID"] = request_id
    return response
