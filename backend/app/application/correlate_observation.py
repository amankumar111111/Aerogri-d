"""Use case: Correlate a new observation with existing signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.entities import Signal, SignalEvent
from app.domain.policies import (
    CorrelationConfig,
    DEFAULT_CONFIG,
    composite_score,
    environmental_score,
    independence_score,
    semantic_score,
    spatial_score,
    temporal_score,
)
from app.domain.ports import EventBus, SignalEventStore, SignalStore
from app.domain.value_objects import ConfidenceScore, ContributionEntry, Location, SignalState


@dataclass
class CorrelateRequest:
    observation_id: str
    fingerprint: str
    category: str
    location: Location
    timestamp: datetime
    device_id: str
    evidence_categories: list[str]
    evidence_descriptions: list[str]
    interpretation_confidence: float
    environmental_context: dict | None = None


@dataclass
class CorrelateResponse:
    signal_id: str
    state: SignalState
    composite_score: float
    is_new_signal: bool


class CorrelateObservationUseCase:
    def __init__(
        self,
        signal_store: SignalStore,
        signal_event_store: SignalEventStore,
        event_bus: EventBus,
        config: CorrelationConfig | None = None,
    ) -> None:
        self.signal_store = signal_store
        self.signal_event_store = signal_event_store
        self.event_bus = event_bus
        self.config = config or DEFAULT_CONFIG

    async def execute(self, request: CorrelateRequest) -> CorrelateResponse:
        existing_signals = await self.signal_store.list_(limit=100)

        best_match: Signal | None = None
        best_score = 0.0
        # C3 FIX: Initialize dimension scores to prevent NameError if no signals match
        sem = sp = tmp = indep = 0.0

        for signal in existing_signals:
            if signal.state == SignalState.ARCHIVED:
                continue

            distance = signal.location.distance_to(request.location)
            time_delta = (request.timestamp - signal.created_at).total_seconds() / 60.0

            sem = semantic_score(
                signal.category,
                request.category,
                evidence_overlap=0.5,
            )
            sp = spatial_score(distance)
            tmp = temporal_score(time_delta)
            indep = independence_score(
                is_duplicate=False,
                same_device=False,  # C2 FIX: Signal doesn't track device_id; cannot determine same device
            )
            env = environmental_score(**(request.environmental_context or {}))

            score = composite_score(
                semantic=sem,
                spatial=sp,
                temporal=tmp,
                independence=indep,
                environmental=env,
            )

            # Spatial gate: observations beyond gate radius cannot correlate
            if distance > self.config.spatial_gate_radius_meters:
                score = 0.0

            if score > best_score:
                best_score = score
                best_match = signal

        env_ctx = request.environmental_context or {}
        # Extract boolean flags for environmental_score (ignore non-boolean keys like temperature)
        env_flags = {
            k: v for k, v in env_ctx.items()
            if isinstance(v, bool) and k in (
                "wind_consistent", "low_humidity_high_temp",
                "recent_precipitation", "firms_fire_detected", "cpcb_elevated",
            )
        }
        env_score = environmental_score(**env_flags)

        contribution = ContributionEntry(
            observation_id=request.observation_id,
            fingerprint=request.fingerprint,
            dimension_scores={
                "semantic": sem if best_match else 0.0,
                "spatial": sp if best_match else 0.0,
                "temporal": tmp if best_match else 0.0,
                "independence": indep if best_match else 1.0,
                "environmental": env_score,
            },
            contribution_score=best_score if best_match else 0.0,
            weighted_contribution=best_score * 0.7 if best_match else 0.0,
            evaluation_timestamp=request.timestamp,
        )

        if best_match and best_score >= self.config.threshold_watch:
            return await self._add_to_existing_signal(
                best_match, contribution, best_score, env_ctx
            )

        new_signal = Signal(
            location=request.location,
            category=request.category,
            confidence=ConfidenceScore(value=best_score),
            contributing_observation_ids=[request.observation_id],
            contributions=[contribution],
            environmental_context=env_ctx,
            state=SignalState.WATCH if best_score >= self.config.threshold_watch else SignalState.WATCH,
        )

        await self.signal_store.save(new_signal)

        event = SignalEvent(
            signal_id=new_signal.id,
            sequence_number=1,
            event_type="created",
            new_state=new_signal.state,
            composite_score=best_score,
            contribution_entries=[contribution],
            trigger="correlation_engine",
        )
        await self.signal_event_store.save(event)

        await self.event_bus.publish(
            "SignalCreated",
            {
                "signal_id": new_signal.id,
                "policy_version": "2.0",
                "initial_confidence": best_score,
                "contributing_observations": [request.observation_id],
            },
        )

        return CorrelateResponse(
            signal_id=new_signal.id,
            state=new_signal.state,
            composite_score=best_score,
            is_new_signal=True,
        )

    async def _add_to_existing_signal(
        self,
        signal: Signal,
        contribution: ContributionEntry,
        score: float,
        env_ctx: dict,
    ) -> CorrelateResponse:
        signal.contributing_observation_ids.append(contribution.observation_id)
        signal.contributions.append(contribution)
        signal.confidence = ConfidenceScore(value=score)
        signal.environmental_context = env_ctx
        signal.version += 1
        signal.updated_at = datetime.now(timezone.utc)

        new_state = signal.state
        if (
            signal.state == SignalState.WATCH
            and score >= self.config.threshold_probable_hotspot
            and len(signal.contributing_observation_ids) >= self.config.min_observations_probable_hotspot
        ):
            new_state = SignalState.PROBABLE_HOTSPOT
        elif (
            signal.state == SignalState.PROBABLE_HOTSPOT
            and score >= self.config.threshold_high_confidence
            and len(signal.contributing_observation_ids) >= self.config.min_observations_high_confidence
        ):
            new_state = SignalState.HIGH_CONFIDENCE

        previous_state = signal.state
        signal.state = new_state

        await self.signal_store.save(signal)

        seq = await self.signal_event_store.next_sequence(signal.id)
        event = SignalEvent(
            signal_id=signal.id,
            sequence_number=seq,
            event_type="escalated" if new_state != previous_state else "observation_added",
            previous_state=previous_state,
            new_state=new_state,
            composite_score=score,
            contribution_entries=[contribution],
            trigger="correlation_engine",
        )
        await self.signal_event_store.save(event)

        if new_state != previous_state:
            await self.event_bus.publish(
                "SignalEscalated",
                {
                    "signal_id": signal.id,
                    "previous_state": previous_state.value,
                    "new_state": new_state.value,
                    "composite_score": score,
                },
            )

        return CorrelateResponse(
            signal_id=signal.id,
            state=new_state,
            composite_score=score,
            is_new_signal=False,
        )
