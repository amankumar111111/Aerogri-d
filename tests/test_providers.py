"""Tests for external provider adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.providers.weather import WeatherProvider
from app.infrastructure.providers.firms import FIRMSProvider
from app.infrastructure.providers.cpcb import CPCBProvider


class TestWeatherProvider:
    @pytest.mark.asyncio
    async def test_fetch_returns_normalized_data(self) -> None:
        provider = WeatherProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 38,
                "relative_humidity_2m": 35,
                "wind_speed_10m": 12,
                "wind_direction_180": 45,
                "precipitation": 0,
                "time": "2024-01-15T10:30",
            }
        }
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.provider_type == "weather"
        assert result.status == "available"
        assert result.normalized_data["temperature"] == 38
        assert result.normalized_data["humidity"] == 35
        assert result.normalized_data["low_humidity_high_temp"] is True
        assert result.normalized_data["recent_precipitation"] is False
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_fetch_unavailable_returns_error(self) -> None:
        provider = WeatherProvider()

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=Exception("timeout")):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.status == "unavailable"
        assert result.confidence == 0.0


class TestFIRMSProvider:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_unavailable(self) -> None:
        provider = FIRMSProvider(api_key="")
        result = await provider.fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_fetch_with_fire_detection(self) -> None:
        provider = FIRMSProvider(api_key="test-key")
        csv_data = "latitude,longitude,brightness,scan,track,acq_date,confidence\n19.07,72.88,320.5,1.2,1.1,2024-01-15,80\n"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = csv_data
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["fire_detected"] is True
        assert result.normalized_data["detection_count"] == 1
        assert result.confidence > 0


class TestCPCBProvider:
    @pytest.mark.asyncio
    async def test_no_api_url_returns_unavailable(self) -> None:
        provider = CPCBProvider()
        result = await provider.fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"
        assert result.normalized_data["elevated"] is False
