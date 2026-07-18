"""CPCB government air quality monitoring station provider."""

from __future__ import annotations

import time

import httpx

from app.config.settings import settings
from app.domain.entities import ProviderRecord
from app.domain.ports import DataProvider


class CPCBProvider(DataProvider):
    def __init__(self) -> None:
        self.base_url = settings.cpcb_api_url

    async def fetch(
        self, *, latitude: float, longitude: float, time_range: str | None = None
    ) -> ProviderRecord:
        if not self.base_url:
            return ProviderRecord(
                provider_type="cpcb",
                status="unavailable",
                confidence=0.0,
                latency_ms=0.0,
                normalized_data={"elevated": False},
            )

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/stations",
                    params={"lat": latitude, "lon": longitude, "radius": 50},
                )
                resp.raise_for_status()
            latency = (time.monotonic() - start) * 1000

            data = resp.json()
            stations = data.get("stations", [])

            aqi_values = [s.get("aqi", 0) for s in stations if s.get("aqi")]
            avg_aqi = sum(aqi_values) / len(aqi_values) if aqi_values else 0
            elevated = avg_aqi > 100

            return ProviderRecord(
                provider_type="cpcb",
                raw_data=data,
                normalized_data={
                    "elevated": elevated,
                    "avg_aqi": avg_aqi,
                    "station_count": len(stations),
                    "pm25": next((s.get("pm25") for s in stations if s.get("pm25")), None),
                },
                freshness=stations[0].get("last_update", "") if stations else "",
                status="available",
                confidence=0.85,
                latency_ms=latency,
            )
        except Exception:
            latency = (time.monotonic() - start) * 1000
            return ProviderRecord(
                provider_type="cpcb",
                status="unavailable",
                confidence=0.0,
                latency_ms=latency,
                normalized_data={"elevated": False},
            )

    async def health_check(self) -> dict:
        if not self.base_url:
            return {"status": "degraded", "reason": "no API URL configured"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/stations", params={"lat": 0, "lon": 0, "radius": 1})
                return {"status": "healthy" if resp.status_code == 200 else "degraded"}
        except Exception:
            return {"status": "down"}
