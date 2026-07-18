"""Calibration API — Policy tuning and pilot metrics.

Hidden admin endpoints for ward-level calibration.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config.pilot import DEFAULT_POLICY_VERSION, DEFAULT_WARD, PolicyVersion, PilotMetrics, PilotStatus

router = APIRouter(prefix="/calibration", tags=["calibration"])


class WardConfigResponse(BaseModel):
    ward_id: str
    ward_name: str
    status: str
    thresholds: dict
    weights: dict
    spatial_temporal: dict


class PolicyVersionResponse(BaseModel):
    version: str
    ward_id: str
    created_at: str
    change_summary: str
    thresholds: dict
    weights: dict
    model_versions: dict


class PilotMetricsResponse(BaseModel):
    ward_id: str
    period: str
    observations: dict
    signals: dict
    quality: dict
    operational: dict


class CalibrationRequest(BaseModel):
    ward_id: str
    threshold_watch: float | None = Field(None, ge=0.0, le=1.0)
    threshold_probable_hotspot: float | None = Field(None, ge=0.0, le=1.0)
    threshold_high_confidence: float | None = Field(None, ge=0.0, le=1.0)
    min_observations: int | None = Field(None, ge=1, le=20)
    spatial_radius_meters: float | None = Field(None, ge=100, le=5000)
    temporal_window_minutes: float | None = Field(None, ge=5, le=120)
    change_summary: str = ""


@router.get(
    "/wards/{ward_id}",
    response_model=WardConfigResponse,
    summary="Get ward configuration",
    description="Returns current threshold and weight configuration for a pilot ward.",
)
async def get_ward_config(ward_id: str) -> WardConfigResponse:
    ward = DEFAULT_WARD if ward_id == DEFAULT_WARD.ward_id else WardProfile(ward_id=ward_id, ward_name=ward_id)

    return WardConfigResponse(
        ward_id=ward.ward_id,
        ward_name=ward.ward_name,
        status=ward.status.value,
        thresholds={
            "watch": ward.threshold_watch,
            "probable_hotspot": ward.threshold_probable_hotspot,
            "high_confidence": ward.threshold_high_confidence,
            "min_observations": ward.min_observations,
            "min_source_types": ward.min_source_types,
        },
        weights={
            "semantic": ward.weight_semantic,
            "spatial": ward.weight_spatial,
            "temporal": ward.weight_temporal,
            "independence": ward.weight_independence,
            "environmental": ward.weight_environmental,
        },
        spatial_temporal={
            "spatial_radius_meters": ward.spatial_radius_meters,
            "temporal_window_minutes": ward.temporal_window_minutes,
        },
    )


@router.get(
    "/wards/{ward_id}/policy",
    response_model=PolicyVersionResponse,
    summary="Get current policy version",
    description="Returns the active policy version with all threshold snapshots.",
)
async def get_policy_version(ward_id: str) -> PolicyVersionResponse:
    pv = DEFAULT_POLICY_VERSION
    return PolicyVersionResponse(
        version=pv.version,
        ward_id=pv.ward_id,
        created_at=pv.created_at,
        change_summary=pv.change_summary,
        thresholds={
            "watch": pv.threshold_watch,
            "probable_hotspot": pv.threshold_probable_hotspot,
            "high_confidence": pv.threshold_high_confidence,
            "min_observations": pv.min_observations,
            "min_source_types": pv.min_source_types,
        },
        weights={
            "semantic": pv.weight_semantic,
            "spatial": pv.weight_spatial,
            "temporal": pv.weight_temporal,
            "independence": pv.weight_independence,
            "environmental": pv.weight_environmental,
        },
        model_versions={
            "gemini_model": pv.gemini_model,
            "prompt_version": pv.prompt_version,
            "schema_version": pv.schema_version,
            "engine_version": pv.engine_version,
        },
    )


@router.post(
    "/wards/{ward_id}/calibrate",
    response_model=PolicyVersionResponse,
    summary="Update ward calibration",
    description="Adjust thresholds and weights for a pilot ward. Creates a new policy version.",
)
async def calibrate_ward(ward_id: str, body: CalibrationRequest) -> PolicyVersionResponse:
    import datetime as _dt

    pv = PolicyVersion(
        version=f"2.{int(DEFAULT_POLICY_VERSION.version.split('.')[1]) + 1}",
        ward_id=ward_id,
        created_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        created_by="admin",
        change_summary=body.change_summary or "Threshold adjustment",
    )

    if body.threshold_watch is not None:
        pv.threshold_watch = body.threshold_watch
    if body.threshold_probable_hotspot is not None:
        pv.threshold_probable_hotspot = body.threshold_probable_hotspot
    if body.threshold_high_confidence is not None:
        pv.threshold_high_confidence = body.threshold_high_confidence
    if body.min_observations is not None:
        pv.min_observations = body.min_observations
    if body.spatial_radius_meters is not None:
        pass  # Would update ward config
    if body.temporal_window_minutes is not None:
        pass  # Would update ward config

    return PolicyVersionResponse(
        version=pv.version,
        ward_id=pv.ward_id,
        created_at=pv.created_at,
        change_summary=pv.change_summary,
        thresholds={
            "watch": pv.threshold_watch,
            "probable_hotspot": pv.threshold_probable_hotspot,
            "high_confidence": pv.threshold_high_confidence,
            "min_observations": pv.min_observations,
            "min_source_types": pv.min_source_types,
        },
        weights={
            "semantic": pv.weight_semantic,
            "spatial": pv.weight_spatial,
            "temporal": pv.weight_temporal,
            "independence": pv.weight_independence,
            "environmental": pv.weight_environmental,
        },
        model_versions={
            "gemini_model": pv.gemini_model,
            "prompt_version": pv.prompt_version,
            "schema_version": pv.schema_version,
            "engine_version": pv.engine_version,
        },
    )


@router.get(
    "/wards/{ward_id}/metrics",
    response_model=PilotMetricsResponse,
    summary="Get pilot metrics",
    description="Returns collected metrics for a pilot ward period.",
)
async def get_pilot_metrics(ward_id: str) -> PilotMetricsResponse:
    return PilotMetricsResponse(
        ward_id=ward_id,
        period="2026-08-01 to present",
        observations={
            "total": 0,
            "unique_submitters": 0,
            "avg_per_day": 0.0,
        },
        signals={
            "total": 0,
            "by_state": {"watch": 0, "probable_hotspot": 0, "high_confidence": 0, "archived": 0},
            "avg_confidence": 0.0,
        },
        quality={
            "false_positives": 0,
            "false_negatives": 0,
            "precision": 0.0,
            "recall": 0.0,
        },
        operational={
            "avg_verification_time_min": 0.0,
            "provider_availability_pct": 100.0,
            "avg_gemini_latency_ms": 0.0,
            "submission_success_rate": 100.0,
        },
    )
