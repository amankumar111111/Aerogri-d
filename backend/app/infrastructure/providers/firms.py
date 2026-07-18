"""NASA FIRMS satellite fire detection provider."""

from __future__ import annotations

import time

import httpx

from app.config.settings import settings
from app.domain.entities import ProviderRecord
from app.domain.ports import DataProvider


class FIRMSProvider(DataProvider):
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or ""
        self.base_url = settings.firms_api_url or "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    async def fetch(
        self, *, latitude: float, longitude: float, time_range: str | None = None
    ) -> ProviderRecord:
        if not self.api_key:
            return ProviderRecord(
                provider_type="firms",
                status="unavailable",
                confidence=0.0,
                latency_ms=0.0,
            )

        params = {
            "KEY": self.api_key,
            "SOURCE": "VIIRS_SNPP_NRT",
            "LAT": latitude,
            "LON": longitude,
            "RAD": 10,
            "DAY_RANGE": 1,
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
            latency = (time.monotonic() - start) * 1000

            lines = resp.text.strip().split("\n")
            detections = []
            if len(lines) > 1:
                headers = lines[0].split(",")
                for line in lines[1:]:
                    values = line.split(",")
                    if len(values) >= len(headers):
                        detections.append(dict(zip(headers, values)))

            fire_detected = len(detections) > 0
            max_confidence = max((float(d.get("confidence", 0)) for d in detections), default=0)

            return ProviderRecord(
                provider_type="firms",
                raw_data={"csv": resp.text[:1000]},
                normalized_data={
                    "fire_detected": fire_detected,
                    "detection_count": len(detections),
                    "max_confidence": max_confidence,
                },
                freshness=detections[0].get("acq_date", "") if detections else "",
                status="available",
                confidence=min(1.0, max_confidence / 100) if fire_detected else 0.0,
                latency_ms=latency,
            )
        except Exception:
            latency = (time.monotonic() - start) * 1000
            return ProviderRecord(
                provider_type="firms",
                status="unavailable",
                confidence=0.0,
                latency_ms=latency,
            )

    async def health_check(self) -> dict:
        return {"status": "healthy" if self.api_key else "degraded"}
