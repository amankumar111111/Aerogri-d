"""Weather provider — Open-Meteo API adapter."""

from __future__ import annotations

import time

import httpx

from app.config.settings import settings
from app.domain.entities import ProviderRecord
from app.domain.ports import DataProvider


class WeatherProvider(DataProvider):
    def __init__(self) -> None:
        self.base_url = settings.weather_api_url

    async def fetch(
        self, *, latitude: float, longitude: float, time_range: str | None = None
    ) -> ProviderRecord:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation",
            "past_hours": 3,
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/forecast", params=params)
                resp.raise_for_status()
            data = resp.json()
            latency = (time.monotonic() - start) * 1000

            current = data.get("current", {})
            humidity = current.get("relative_humidity_2m", 50)
            temp = current.get("temperature_2m", 25)
            wind_dir = current.get("wind_direction_10m", 0)
            precipitation = current.get("precipitation", 0)

            return ProviderRecord(
                provider_type="weather",
                raw_data=data,
                normalized_data={
                    "temperature": temp,
                    "humidity": humidity,
                    "wind_speed": current.get("wind_speed_10m", 0),
                    "wind_direction": wind_dir,
                    "precipitation": precipitation,
                    "low_humidity_high_temp": humidity < 40 and temp > 35,
                    "recent_precipitation": precipitation > 0,
                },
                freshness=data.get("current", {}).get("time", ""),
                status="available",
                confidence=0.9,
                latency_ms=latency,
            )
        except Exception:
            latency = (time.monotonic() - start) * 1000
            return ProviderRecord(
                provider_type="weather",
                status="unavailable",
                confidence=0.0,
                latency_ms=latency,
            )

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/forecast", params={"latitude": 0, "longitude": 0, "current": "temperature_2m"})
                return {"status": "healthy" if resp.status_code == 200 else "degraded"}
        except Exception:
            return {"status": "down"}
