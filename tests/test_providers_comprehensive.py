"""Integration Tests — Providers & Failure Injection.

Tests each provider independently with all failure modes.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.infrastructure.providers.weather import WeatherProvider
from app.infrastructure.providers.firms import FIRMSProvider
from app.infrastructure.providers.cpcb import CPCBProvider
from app.domain.entities import ProviderRecord


# ============================================================
# Weather Provider — All Scenarios
# ============================================================

class TestWeatherProviderComprehensive:
    @pytest.mark.asyncio
    async def test_success_normal_conditions(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "current": {"temperature_2m": 25, "relative_humidity_2m": 60,
                        "wind_speed_10m": 10, "wind_direction_180": 90,
                        "precipitation": 0, "time": "2024-01-15T10:30"}
        }
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["temperature"] == 25
        assert result.normalized_data["low_humidity_high_temp"] is False

    @pytest.mark.asyncio
    async def test_success_hot_dry_conditions(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "current": {"temperature_2m": 42, "relative_humidity_2m": 20,
                        "wind_speed_10m": 15, "wind_direction_180": 180,
                        "precipitation": 0, "time": "2024-01-15T10:30"}
        }
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.normalized_data["low_humidity_high_temp"] is True
        assert result.normalized_data["recent_precipitation"] is False

    @pytest.mark.asyncio
    async def test_success_with_rain(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "current": {"temperature_2m": 20, "relative_humidity_2m": 90,
                        "wind_speed_10m": 5, "wind_direction_180": 0,
                        "precipitation": 5.0, "time": "2024-01-15T10:30"}
        }
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.normalized_data["recent_precipitation"] is True
        assert result.normalized_data["low_humidity_high_temp"] is False

    @pytest.mark.asyncio
    async def test_timeout(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_network_failure(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_resp)

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().health_check()

        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=Exception("down"))

        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().health_check()

        assert result["status"] == "down"


# ============================================================
# FIRMS Provider — All Scenarios
# ============================================================

class TestFIRMSProviderComprehensive:
    @pytest.mark.asyncio
    async def test_success_with_detections(self):
        csv_data = "latitude,longitude,brightness,scan,track,acq_date,confidence\n19.07,72.88,320.5,1.2,1.1,2024-01-15,80\n"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = csv_data
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await FIRMSProvider(api_key="test-key").fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["fire_detected"] is True
        assert result.normalized_data["detection_count"] == 1

    @pytest.mark.asyncio
    async def test_success_no_detections(self):
        csv_data = "latitude,longitude,brightness,scan,track,acq_date,confidence\n"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = csv_data
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=client):
            result = await FIRMSProvider(api_key="test-key").fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["fire_detected"] is False
        assert result.normalized_data["detection_count"] == 0

    @pytest.mark.asyncio
    async def test_no_api_key(self):
        result = await FIRMSProvider(api_key="").fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_timeout(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("httpx.AsyncClient", return_value=client):
            result = await FIRMSProvider(api_key="key").fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_network_failure(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("httpx.AsyncClient", return_value=client):
            result = await FIRMSProvider(api_key="key").fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_health_check_with_key(self):
        result = await FIRMSProvider(api_key="key").health_check()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_without_key(self):
        result = await FIRMSProvider(api_key="").health_check()
        assert result["status"] == "degraded"


# ============================================================
# CPCB Provider — All Scenarios
# ============================================================

class TestCPCBProviderComprehensive:
    @pytest.mark.asyncio
    async def test_success_normal_aqi(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "stations": [{"aqi": 80, "pm25": 45, "last_update": "2024-01-15T10:30"}]
        }
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        provider = CPCBProvider()
        provider.base_url = "http://test-api"

        with patch("httpx.AsyncClient", return_value=client):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["elevated"] is False
        assert result.normalized_data["avg_aqi"] == 80

    @pytest.mark.asyncio
    async def test_success_elevated_aqi(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "stations": [{"aqi": 150, "pm25": 90, "last_update": "2024-01-15T10:30"}]
        }
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        provider = CPCBProvider()
        provider.base_url = "http://test-api"

        with patch("httpx.AsyncClient", return_value=client):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.normalized_data["elevated"] is True

    @pytest.mark.asyncio
    async def test_empty_response(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stations": []}
        mock_resp.raise_for_status = lambda: None

        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)

        provider = CPCBProvider()
        provider.base_url = "http://test-api"

        with patch("httpx.AsyncClient", return_value=client):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["elevated"] is False

    @pytest.mark.asyncio
    async def test_no_url(self):
        result = await CPCBProvider().fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_timeout(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        provider = CPCBProvider()
        provider.base_url = "http://test-api"

        with patch("httpx.AsyncClient", return_value=client):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_network_failure(self):
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        provider = CPCBProvider()
        provider.base_url = "http://test-api"

        with patch("httpx.AsyncClient", return_value=client):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_health_check_no_url(self):
        result = await CPCBProvider().health_check()
        assert result["status"] == "degraded"
