"""API integration tests — verify endpoints, validation, error responses."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import AppError, app_error_handler, correlation_id_middleware
from app.api.routers import analytics, health, observations, signals
from app.application.submit_observation import SubmitObservationUseCase
from app.infrastructure.db import Base
from app.infrastructure.repositories import (
    SQLAlchemyAuditLog,
    SQLAlchemyObservationStore,
    InMemoryEventBus,
)
from starlette.middleware.cors import CORSMiddleware


@pytest.fixture
def client() -> TestClient:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    test_app = FastAPI()
    test_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    test_app.middleware("http")(correlation_id_middleware)
    test_app.add_exception_handler(AppError, app_error_handler)

    session = TestSession()
    obs_store = SQLAlchemyObservationStore(session)
    audit_log = SQLAlchemyAuditLog(session)
    event_bus = InMemoryEventBus()

    test_app.state.submit_observation_uc = SubmitObservationUseCase(obs_store, audit_log, event_bus)
    test_app.state.db_session = session

    test_app.include_router(observations.router, prefix="/api/v1")
    test_app.include_router(signals.router, prefix="/api/v1")
    test_app.include_router(analytics.router, prefix="/api/v1")
    test_app.include_router(health.router, prefix="/api/v1")

    with TestClient(test_app) as c:
        yield c


class TestHealthAPI:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestObservationAPI:
    def test_submit_observation_valid(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/observations",
            json={
                "content": "I see heavy smoke from the factory",
                "latitude": 19.076,
                "longitude": 72.878,
                "category": "smoke",
                "language": "en",
                "device_id": "device-123",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "observation_id" in data
        assert "fingerprint" in data
        assert data["status"] == "submitted"
        assert "tracking_ref" in data

    def test_submit_observation_missing_content(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/observations",
            json={
                "content": "",
                "latitude": 19.076,
                "longitude": 72.878,
                "category": "smoke",
                "language": "en",
                "device_id": "device-123",
            },
        )
        assert resp.status_code == 422

    def test_submit_observation_invalid_category(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/observations",
            json={
                "content": "Smoke visible",
                "latitude": 19.076,
                "longitude": 72.878,
                "category": "invalid_category",
                "language": "en",
                "device_id": "device-123",
            },
        )
        assert resp.status_code == 422

    def test_submit_observation_returns_correlation_id(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/observations",
            json={
                "content": "Test",
                "latitude": 19.0,
                "longitude": 72.0,
                "category": "smoke",
                "language": "en",
                "device_id": "device-1",
            },
            headers={"X-Correlation-ID": "test-correlation-123"},
        )
        assert resp.headers.get("X-Correlation-ID") == "test-correlation-123"
        assert "X-Response-Time" in resp.headers


class TestSignalAPI:
    def test_list_signals_empty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/signals")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_signal_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/signals/nonexistent")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"]["code"] == "NOT_FOUND"


class TestAnalyticsAPI:
    def test_analytics_returns_summary(self, client: TestClient) -> None:
        resp = client.get("/api/v1/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_observations" in data
        assert "total_signals" in data

    def test_heatmap_returns_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/analytics/heatmap")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_timeline_returns_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/analytics/timeline")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
