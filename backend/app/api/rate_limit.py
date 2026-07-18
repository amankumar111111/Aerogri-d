"""Rate Limiting Middleware.

Enforces per-IP, per-device, and per-session rate limits.
"""

from __future__ import annotations

import time
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.domain.ports import RateLimiter


async def rate_limit_middleware(request: Request, call_next, rate_limiter: RateLimiter):
    """Rate limiting middleware — checks limits before processing."""

    # Skip rate limiting for exempt paths
    path = request.url.path
    exempt = ["/health", "/ready", "/metrics", "/api/v1/health", "/api/v1/ready", "/api/v1/metrics"]
    if any(path.startswith(e) for e in exempt) or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    # Determine rate limit key and limits
    client_ip = request.client.host if request.client else "unknown"
    device_id = request.headers.get("X-Device-ID", client_ip)

    # Per-IP limit
    ip_key = f"ip:{client_ip}"
    if not await rate_limiter.check(ip_key, settings.rate_limit_per_ip, 60):
        remaining = await rate_limiter.get_remaining(ip_key, settings.rate_limit_per_ip, 60)
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": f"Rate limit exceeded. Try again in 60 seconds.",
                    "retry_after": 60,
                }
            },
            headers={"Retry-After": "60", "X-RateLimit-Limit": str(settings.rate_limit_per_ip), "X-RateLimit-Remaining": str(remaining)},
        )

    # Per-device limit (observation submissions only)
    if request.method == "POST" and "/observations" in path:
        device_key = f"device:{device_id}"
        if not await rate_limiter.check(device_key, settings.rate_limit_per_device, 3600):
            remaining = await rate_limiter.get_remaining(device_key, settings.rate_limit_per_device, 3600)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"Device observation limit exceeded. Try again in 1 hour.",
                        "retry_after": 3600,
                    }
                },
                headers={"Retry-After": "3600", "X-RateLimit-Limit": str(settings.rate_limit_per_device), "X-RateLimit-Remaining": str(remaining)},
            )

    return await call_next(request)
