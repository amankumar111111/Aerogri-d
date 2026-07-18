"""Idempotency Middleware.

Prevents duplicate submissions by:
1. Checking explicit Idempotency-Key header
2. Checking fingerprint + device_id combination
"""

from __future__ import annotations

import json
from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.ports import IdempotencyStore


async def idempotency_middleware(request: Request, call_next, idempotency_store: IdempotencyStore):
    """Idempotency check — only for POST /observations."""

    # Only apply to observation submissions
    if request.method != "POST" or "/observations" not in request.url.path:
        return await call_next(request)

    # Check explicit Idempotency-Key header
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        existing = await idempotency_store.check_and_set(
            key=f"header:{idempotency_key}",
            response="",
            ttl_seconds=300,
        )
        if existing is not None:
            return JSONResponse(
                status_code=200,
                content=json.loads(existing),
                headers={"X-Idempotent": "true"},
            )

    # Process the request
    response = await call_next(request)

    # Store successful responses for idempotency
    if response.status_code == 201:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        response_body = body.decode()

        # Build idempotency key from fingerprint + device_id
        try:
            data = json.loads(response_body)
            fingerprint = data.get("fingerprint", "")
            device_id = request.headers.get("X-Device-ID", "")
            if fingerprint and device_id:
                key = f"fp:{fingerprint}:{device_id}"
                await idempotency_store.check_and_set(
                    key=key,
                    response=response_body,
                    ttl_seconds=300,
                )
        except (json.JSONDecodeError, KeyError):
            pass

        # Reconstruct response (body_iterator consumed)
        return JSONResponse(
            status_code=201,
            content=json.loads(response_body),
            headers=dict(response.headers),
        )

    return response
