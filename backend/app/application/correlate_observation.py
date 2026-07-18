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


def _score_signal_against_observation(
    signal: Signal,
    request: CorrelateRequest,
    config: CorrelationConfig,
) -> float:
    """Score how well an existing signal matches a new observation."""
    distance = signal.location.distance_to(request.location)
    time_delta = (request.timestamp - signal.created_at).total_seconds() / 60.0

    sem = semantic_score(signal.category, request.category, evidence_overlap=0.5)
    sp = spatial_score(distance)
    tmp = temporal_score(time_delta)
    indep = independence_score(is_duplicate=False, same_device=False)

    env_ctx = request.environmental_context or {}
    env_flags = {
        k: v for k, v in env_ctx.items()
        if isinstance(v, bool) and k in (
            "wind_consistent", "low_humidity_high_temp",
            "recent_precipitation", "firms_fire_detected", "cpcb_elevated",
        )
    }
    env = environmental_score(**env_flags)

    score = composite_score(semantic=sem, spatial=sp, temporal=tmp, independence=indep, environmental=env)

    if distance > config.spatial_gate_radius_meters:
        score = 0.0

    return score


def _build_contribution(
    request: CorrelateRequest,
    best_match: Signal | None,
    best_score: float,
    env_ctx: dict,
) -> ContributionEntry:
    """Build a ContributionEntry recording how this observation scored."""
    env_flags = {
        k: v for k, v in env_ctx.items()
        if isinstance(v, bool) and k in (
            "wind_consistent", "low_humidity_high_temp",
            "recent_precipitation", "firms_fire_detected", "cpcb_elevated",
        )
    }
    env_score = environmental_score(**env_flags)

    return ContributionEntry(
        observation_id=request.observation_id,
        fingerprint=request.fingerprint,
        dimension_scores={
            "semantic": 0.0,
            "spatial": 0.0,
            "temporal": 0.0,
            "independence": 1.0,
            "environmental": env_score,
        },
        contribution_score=best_score if best_match else 0.0,
        weighted_contribution=best_score * 0.7 if best_match else 0.0,
        evaluation_timestamp=request.timestamp,
    )


def _find_best_match(
    existing_signals: list[Signal],
    request: CorrelateRequest,
    config: CorrelationConfig,
) -> tuple[Signal | None, float]:
    """Find the best matching signal for a new observation."""
    best_match: Signal | None = None
    best_score = 0.0

    for signal in existing_signals:
        if signal.state == SignalState.ARCHIVED:
            continue
        score = _score_signal_against_observation(signal, request, config)
        if score > best_score:
            best_score = score
            best_match = signal

    return best_match, best_score


def _determine_new_state(signal: Signal, score: float, config: CorrelationConfig) -> SignalState:
    """Determine if a signal should transition to a new state."""
    if (
        signal.state == SignalState.WATCH
        and score >= config.threshold_probable_hotspot
        and len(signal.contributing_observation_ids) >= config.min_observations_probable_hotspot
    ):
        return SignalState.PROBABLE_HOTSPOT
    elif (
        signal.state == SignalState.PROBABLE_HOTSPOT
        and score >= config.threshold_high_confidence
        and len(signal.contributing_observation_ids) >= config.min_observations_high_confidence
    ):
        return SignalState.HIGH_CONFIDENCE
    return signal.state


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
        best_match, best_score = _find_best_match(existing_signals, request, self.config)

        env_ctx = request.environmental_context or {}
        contribution = _build_contribution(request, best_match, best_score, env_ctx)

        if best_match and best_score >= self.config.threshold_watch:
            return await self._add_to_existing_signal(best_match, contribution, best_score, env_ctx)

        return await self._create_new_signal(request, contribution, best_score, env_ctx)

    async def _create_new_signal(
        self,
        request: CorrelateRequest,
        contribution: ContributionEntry,
        score: float,
        env_ctx: dict,
    ) -> CorrelateResponse:
        signal = Signal(
            location=request.location,
            category=request.category,
            confidence=ConfidenceScore(value=score),
            contributing_observation_ids=[request.observation_id],
            contributions=[contribution],
            environmental_context=env_ctx,
            state=SignalState.WATCH,
        )
        await self.signal_store.save(signal)

        event = SignalEvent(
            signal_id=signal.id,
            sequence_number=1,
            event_type="created",
            new_state=signal.state,
            composite_score=score,
            contribution_entries=[contribution],
            trigger="correlation_engine",
        )
        await self.signal_event_store.save(event)

        await self.event_bus.publish("SignalCreated", {
            "signal_id": signal.id,
            "policy_version": "2.0",
            "initial_confidence": score,
            "contributing_observations": [request.observation_id],
        })

        return CorrelateResponse(signal_id=signal.id, state=signal.state, composite_score=score, is_new_signal=True)

    async def _add_to_existing_signal(
        self, signal: Signal, contribution: ContributionEntry, score: float, env_ctx: dict,
    ) -> CorrelateResponse:
        signal.contributing_observation_ids.append(contribution.observation_id)
        signal.contributions.append(contribution)
        signal.confidence = ConfidenceScore(value=score)
        signal.environmental_context = env_ctx
        signal.version += 1
        signal.updated_at = datetime.now(timezone.utc)

        previous_state = signal.state
        signal.state = _determine_new_state(signal, score, self.config)

        await self.signal_store.save(signal)

        seq = await self.signal_event_store.next_sequence(signal.id)
        event = SignalEvent(
            signal_id=signal.id, sequence_number=seq,
            event_type="escalated" if signal.state != previous_state else "observation_added",
            previous_state=previous_state, new_state=signal.state,
            composite_score=score, contribution_entries=[contribution],
            trigger="correlation_engine",
        )
        await self.signal_event_store.save(event)

        if signal.state != previous_state:
            await self.event_bus.publish("SignalEscalated", {
                "signal_id": signal.id,
                "previous_state": previous_state.value,
                "new_state": signal.state.value,
                "composite_score": score,
            })

        return CorrelateResponse(signal_id=signal.id, state=signal.state, composite_score=score, is_new_signal=False)
