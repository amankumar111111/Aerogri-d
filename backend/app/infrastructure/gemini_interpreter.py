"""Gemini adapter implementing the ObservationInterpreter port."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import httpx

from app.config.settings import settings
from app.domain.ports import ObservationInterpreter

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

INTERPRETATION_PROMPT = """You are an environmental observation analyst for AEROGRID.

Analyze the citizen's observation and extract structured environmental data.

Respond with ONLY a JSON object (no markdown, no explanation):
{
  "categories": ["<primary category>"],
  "evidence_descriptions": ["<what is visible/audible>"],
  "severity": {"level": "<low|medium|high|critical>", "indicators": ["<what indicates this severity>"]},
  "citizen_category_alignment": <true if citizen's selected category matches what you see>,
  "confidence": <0.0-1.0 your confidence in this interpretation>
}

Categories: smoke, dust, chemical, water, noise, fire, gas_leak, construction_dust, sewage, other

Focus on what is VISIBLE and MEASURABLE. Do not decide if the incident is real — only interpret the evidence."""


def _build_parts(
    text: str, citizen_category: str, image_bytes: bytes | None, voice_bytes: bytes | None,
) -> list[dict[str, Any]]:
    """Build Gemini API parts from observation inputs."""
    parts: list[dict[str, Any]] = []

    if text or citizen_category:
        prompt_text = f"Citizen selected category: {citizen_category}\n\nObservation: {text}"
        parts.append({"text": f"{INTERPRETATION_PROMPT}\n\n{prompt_text}"})

    if image_bytes:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}})

    if voice_bytes:
        parts.append({"inline_data": {"mime_type": "audio/webm", "data": base64.b64encode(voice_bytes).decode()}})

    return parts


def _no_data_response(citizen_category: str, text: str) -> dict[str, Any]:
    """Return a minimal response when no input data is available."""
    return {
        "categories": [citizen_category or "other"],
        "evidence_descriptions": [text or "No evidence provided"],
        "severity": {"level": "low", "indicators": ["insufficient data"]},
        "citizen_category_alignment": True,
        "confidence": 0.1,
    }


def _extract_text_from_response(data: dict) -> str:
    """Safely extract text from Gemini API response."""
    candidates = data.get("candidates")
    if not candidates:
        raise ValueError(f"Gemini returned no candidates: {data}")

    text_response = (
        candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    )
    if not text_response:
        raise ValueError(f"Gemini returned empty text response: {data}")

    cleaned = text_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n", 1)
        if len(lines) > 1:
            cleaned = lines[1].rsplit("```", 1)[0].strip()

    return cleaned


class GeminiInterpreterAdapter(ObservationInterpreter):
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.timeout = settings.gemini_timeout_seconds
        self.prompt_version = settings.gemini_prompt_version
        self.schema_version = settings.gemini_schema_version

    async def interpret(
        self,
        image_bytes: bytes | None,
        voice_bytes: bytes | None,
        text: str,
        citizen_category: str,
    ) -> dict[str, Any]:
        parts = _build_parts(text, citizen_category, image_bytes, voice_bytes)

        if not parts:
            return _no_data_response(citizen_category, text)

        url = GEMINI_API_URL.format(model=self.model)
        payload = {"contents": [{"parts": parts}]}

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, params={"key": self.api_key})
            response.raise_for_status()
        latency_ms = (time.monotonic() - start) * 1000

        cleaned = _extract_text_from_response(response.json())

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}") from e

        result["_meta"] = {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "schema_version": self.schema_version,
            "latency_ms": latency_ms,
        }
        return result
