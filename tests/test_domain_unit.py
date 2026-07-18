"""Unit Tests — Domain Layer. Target 90%+ coverage.

Every rule, every transition, every edge case.
"""

from __future__ import annotations

import math
import pytest
from datetime import datetime, timedelta, timezone

from app.domain.value_objects import (
    ConfidenceScore,
    ContributionEntry,
    EvidenceWeight,
    Location,
    ObservationFingerprint,
    Severity,
    SeverityLevel,
    SignalState,
    SourceType,
)
from app.domain.entities import (
    AuditEvent,
    Interpretation,
    Notification,
    Observation,
    PolicyVersion,
    ProviderRecord,
    Signal,
    SignalEvent,
)
from app.domain.policies import (
    CATEGORY_RELATIONSHIPS,
    CompositeWeights,
    CorrelationConfig,
    DEFAULT_CONFIG,
    DuplicateConfig,
    SimilarityWeights,
    composite_score,
    compute_similarity,
    environmental_score,
    independence_score,
    is_duplicate,
    semantic_score,
    spatial_score,
    temporal_score,
)


# ============================================================
# Location
# ============================================================

class TestLocation:
    def test_valid_location(self):
        loc = Location(19.076, 72.878)
        assert loc.latitude == 19.076
        assert loc.longitude == 72.878

    def test_invalid_latitude_raises(self):
        with pytest.raises(ValueError):
            Location(91.0, 0.0)
        with pytest.raises(ValueError):
            Location(-91.0, 0.0)

    def test_invalid_longitude_raises(self):
        with pytest.raises(ValueError):
            Location(0.0, 181.0)
        with pytest.raises(ValueError):
            Location(0.0, -181.0)

    def test_boundary_values(self):
        Location(90.0, 180.0)
        Location(-90.0, -180.0)
        Location(0.0, 0.0)

    def test_distance_to_self(self):
        loc = Location(19.076, 72.878)
        assert loc.distance_to(loc) == 0.0

    def test_distance_to_nearby(self):
        a = Location(19.076, 72.877)
        b = Location(19.077, 72.878)
        dist = a.distance_to(b)
        assert 100 < dist < 200

    def test_distance_symmetric(self):
        a = Location(19.076, 72.877)
        b = Location(19.077, 72.878)
        assert abs(a.distance_to(b) - b.distance_to(a)) < 0.001

    def test_is_within_true(self):
        a = Location(19.076, 72.878)
        b = Location(19.0761, 72.8781)
        assert a.is_within(b, 200)

    def test_is_within_false(self):
        a = Location(19.076, 72.878)
        b = Location(19.5, 73.0)
        assert not a.is_within(b, 200)

    def test_grid_bucket(self):
        loc = Location(19.0760, 72.8777)
        assert loc.grid_bucket() == "19.076,72.878"

    def test_grid_bucket_precision(self):
        loc = Location(19.0760, 72.8777)
        assert loc.grid_bucket(precision=2) == "19.08,72.88"


# ============================================================
# Severity
# ============================================================

class TestSeverity:
    def test_exceeds_high_over_low(self):
        assert Severity(SeverityLevel.HIGH).exceeds(Severity(SeverityLevel.LOW))

    def test_not_exceeds_same(self):
        assert not Severity(SeverityLevel.MEDIUM).exceeds(Severity(SeverityLevel.MEDIUM))

    def test_not_exceeds_lower(self):
        assert not Severity(SeverityLevel.LOW).exceeds(Severity(SeverityLevel.HIGH))

    def test_critical_exceeds_all(self):
        for level in [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH]:
            assert Severity(SeverityLevel.CRITICAL).exceeds(Severity(level))


# ============================================================
# EvidenceWeight
# ============================================================

class TestEvidenceWeight:
    def test_government_weight(self):
        w = EvidenceWeight(SourceType.GOVERNMENT, 0.9, 0.0)
        assert w.adjusted_weight() == 0.9

    def test_satellite_weight(self):
        w = EvidenceWeight(SourceType.SATELLITE, 0.85, 0.0)
        assert w.adjusted_weight() == 0.85

    def test_citizen_weight(self):
        w = EvidenceWeight(SourceType.CITIZEN, 0.7, 0.0)
        assert w.adjusted_weight() == 0.7

    def test_decay_over_time(self):
        w = EvidenceWeight(SourceType.CITIZEN, 0.7, 14.0)
        adjusted = w.adjusted_weight()
        assert 0.3 < adjusted < 0.4  # ~50% decay after 14h

    def test_unknown_source_fallback(self):
        w = EvidenceWeight(SourceType.WEATHER, 0.8, 0.0)
        assert w.adjusted_weight() == 0.8


# ============================================================
# ConfidenceScore
# ============================================================

class TestConfidenceScore:
    def test_valid_range(self):
        ConfidenceScore(0.0)
        ConfidenceScore(0.5)
        ConfidenceScore(1.0)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            ConfidenceScore(-0.1)
        with pytest.raises(ValueError):
            ConfidenceScore(1.1)

    def test_meets_threshold(self):
        assert ConfidenceScore(0.7).meets_threshold(0.5)
        assert not ConfidenceScore(0.3).meets_threshold(0.5)
        assert ConfidenceScore(0.5).meets_threshold(0.5)

    def test_classification_watch(self):
        assert ConfidenceScore(0.35).classification() == SignalState.WATCH

    def test_classification_probable_hotspot(self):
        assert ConfidenceScore(0.55).classification() == SignalState.PROBABLE_HOTSPOT

    def test_classification_high_confidence(self):
        assert ConfidenceScore(0.75).classification() == SignalState.HIGH_CONFIDENCE

    def test_classification_archived(self):
        assert ConfidenceScore(0.1).classification() == SignalState.ARCHIVED

    def test_classification_custom_thresholds(self):
        thresholds = {"watch": 0.2, "probable_hotspot": 0.4, "high_confidence": 0.6}
        assert ConfidenceScore(0.5).classification(thresholds) == SignalState.PROBABLE_HOTSPOT


# ============================================================
# ObservationFingerprint
# ============================================================

class TestObservationFingerprint:
    def test_same_inputs_same_hash(self):
        loc = Location(19.076, 72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        a = ObservationFingerprint.compute(b"img", b"voice", loc, ts, "d1")
        b = ObservationFingerprint.compute(b"img", b"voice", loc, ts, "d1")
        assert a.hash == b.hash

    def test_different_device_different_hash(self):
        loc = Location(19.076, 72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        a = ObservationFingerprint.compute(b"img", b"voice", loc, ts, "d1")
        b = ObservationFingerprint.compute(b"img", b"voice", loc, ts, "d2")
        assert a.hash != b.hash

    def test_different_image_different_hash(self):
        loc = Location(19.076, 72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        a = ObservationFingerprint.compute(b"img1", b"voice", loc, ts, "d1")
        b = ObservationFingerprint.compute(b"img2", b"voice", loc, ts, "d1")
        assert a.hash != b.hash

    def test_no_media_still_works(self):
        loc = Location(19.076, 72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        fp = ObservationFingerprint.compute(None, None, loc, ts, "d1")
        assert len(fp.hash) == 64  # SHA-256 hex


# ============================================================
# Duplicate Detection
# ============================================================

class TestDuplicateDetection:
    def test_exact_duplicate(self):
        assert is_duplicate(content_similarity=0.9, spatial_distance_meters=50, temporal_gap_minutes=5)

    def test_high_content_not_duplicate(self):
        assert not is_duplicate(content_similarity=0.9, spatial_distance_meters=300, temporal_gap_minutes=5)

    def test_close_not_duplicate_if_content_different(self):
        assert not is_duplicate(content_similarity=0.3, spatial_distance_meters=50, temporal_gap_minutes=5)

    def test_old_not_duplicate(self):
        assert not is_duplicate(content_similarity=0.9, spatial_distance_meters=50, temporal_gap_minutes=20)

    def test_boundary_content(self):
        assert not is_duplicate(content_similarity=0.85, spatial_distance_meters=50, temporal_gap_minutes=5)
        assert is_duplicate(content_similarity=0.86, spatial_distance_meters=50, temporal_gap_minutes=5)

    def test_boundary_spatial(self):
        assert not is_duplicate(content_similarity=0.9, spatial_distance_meters=200, temporal_gap_minutes=5)
        assert is_duplicate(content_similarity=0.9, spatial_distance_meters=199, temporal_gap_minutes=5)

    def test_boundary_temporal(self):
        assert not is_duplicate(content_similarity=0.9, spatial_distance_meters=50, temporal_gap_minutes=15)
        assert is_duplicate(content_similarity=0.9, spatial_distance_meters=50, temporal_gap_minutes=14)

    def test_custom_config(self):
        config = DuplicateConfig(content_threshold=0.5, spatial_threshold_meters=100, temporal_threshold_minutes=5)
        assert is_duplicate(content_similarity=0.6, spatial_distance_meters=50, temporal_gap_minutes=3, config=config)
        assert not is_duplicate(content_similarity=0.6, spatial_distance_meters=50, temporal_gap_minutes=8, config=config)


# ============================================================
# Similarity Scoring
# ============================================================

class TestSimilarityScoring:
    def test_identical(self):
        s = compute_similarity(
            content_similarity=1.0, spatial_distance_meters=0,
            max_distance_meters=500, temporal_gap_minutes=0, max_window_minutes=30,
        )
        assert s == 1.0

    def test_zero(self):
        s = compute_similarity(
            content_similarity=0.0, spatial_distance_meters=500,
            max_distance_meters=500, temporal_gap_minutes=30, max_window_minutes=30,
        )
        assert s == 0.0

    def test_weighted(self):
        s = compute_similarity(
            content_similarity=1.0, spatial_distance_meters=0,
            max_distance_meters=500, temporal_gap_minutes=0, max_window_minutes=30,
        )
        assert s == 1.0

    def test_custom_weights(self):
        w = SimilarityWeights(content=1.0, spatial=0.0, temporal=0.0)
        s = compute_similarity(
            content_similarity=1.0, spatial_distance_meters=500,
            max_distance_meters=500, temporal_gap_minutes=30, max_window_minutes=30,
            weights=w,
        )
        assert s == 1.0


# ============================================================
# Correlation Engine Dimensions
# ============================================================

class TestSemanticScore:
    def test_same_category(self):
        assert semantic_score("smoke", "smoke", 1.0) == 1.0

    def test_related_category(self):
        score = semantic_score("smoke", "chemical", 0.5)
        assert 0.5 < score < 0.7

    def test_unrelated(self):
        assert semantic_score("smoke", "noise", 0.0) == 0.0

    def test_other_fallback(self):
        score = semantic_score("smoke", "other", 0.0)
        assert score == 0.1 * 0.6

    def test_symmetric(self):
        a = semantic_score("smoke", "fire", 0.5)
        b = semantic_score("fire", "smoke", 0.5)
        assert abs(a - b) < 0.001


class TestSpatialScore:
    def test_co_located(self):
        assert spatial_score(0.0) == 1.0

    def test_at_radius(self):
        assert spatial_score(500.0) == 0.0

    def test_beyond_radius(self):
        assert spatial_score(1000.0) == 0.0

    def test_custom_radius(self):
        assert spatial_score(100.0, radius_meters=100.0) == 0.0


class TestTemporalScore:
    def test_same_time(self):
        assert temporal_score(0.0) == 1.0

    def test_at_window(self):
        assert temporal_score(30.0) == 0.0

    def test_custom_window(self):
        assert temporal_score(60.0, window_minutes=60.0) == 0.0


class TestIndependenceScore:
    def test_not_duplicate(self):
        assert independence_score(is_duplicate=False, same_device=False) == 1.0

    def test_duplicate(self):
        assert independence_score(is_duplicate=True, same_device=False) == 0.0

    def test_same_device_recent(self):
        assert independence_score(is_duplicate=False, same_device=True, same_session_minutes=3.0) == 0.2

    def test_same_device_old(self):
        assert independence_score(is_duplicate=False, same_device=True, same_session_minutes=10.0) == 1.0


class TestEnvironmentalScore:
    def test_neutral(self):
        assert environmental_score() == 0.0

    def test_fire_corroboration(self):
        assert environmental_score(firms_fire_detected=True) == 0.25

    def test_rain_reduces(self):
        assert environmental_score(recent_precipitation=True) == 0.0

    def test_multiple_factors(self):
        score = environmental_score(
            wind_consistent=True, low_humidity_high_temp=True, firms_fire_detected=True,
        )
        assert score == 0.5

    def test_all_factors(self):
        score = environmental_score(
            wind_consistent=True, low_humidity_high_temp=True,
            firms_fire_detected=True, cpcb_elevated=True,
        )
        assert score == 0.7


class TestCompositeScore:
    def test_all_ones(self):
        s = composite_score(semantic=1.0, spatial=1.0, temporal=1.0, independence=1.0, environmental=1.0)
        assert s == 1.0

    def test_all_zeros(self):
        s = composite_score(semantic=0.0, spatial=0.0, temporal=0.0, independence=0.0, environmental=0.0)
        assert s == 0.0

    def test_clamped_to_1(self):
        s = composite_score(semantic=2.0, spatial=2.0, temporal=2.0, independence=2.0, environmental=2.0)
        assert s == 1.0

    def test_clamped_to_0(self):
        s = composite_score(semantic=-1.0, spatial=-1.0, temporal=-1.0, independence=-1.0, environmental=-1.0)
        assert s == 0.0

    def test_weighted_average(self):
        s = composite_score(semantic=1.0, spatial=0.0, temporal=0.0, independence=0.0, environmental=0.0)
        assert abs(s - 0.30) < 0.001

    def test_custom_weights(self):
        w = CompositeWeights(semantic=1.0, spatial=0.0, temporal=0.0, independence=0.0, environmental=0.0)
        s = composite_score(semantic=1.0, spatial=0.0, temporal=0.0, independence=0.0, environmental=0.0, weights=w)
        assert s == 1.0


# ============================================================
# CorrelationConfig
# ============================================================

class TestCorrelationConfig:
    def test_defaults(self):
        config = CorrelationConfig()
        assert config.threshold_watch == 0.3
        assert config.threshold_probable_hotspot == 0.5
        assert config.threshold_high_confidence == 0.7
        assert config.min_observations_watch == 1
        assert config.min_observations_probable_hotspot == 3
        assert config.min_observations_high_confidence == 5

    def test_custom_config(self):
        config = CorrelationConfig(threshold_watch=0.2, threshold_probable_hotspot=0.4)
        assert config.threshold_watch == 0.2
        assert config.threshold_probable_hotspot == 0.4


# ============================================================
# Category Relationships
# ============================================================

class TestCategoryRelationships:
    def test_smoke_smoke(self):
        assert CATEGORY_RELATIONSHIPS[("smoke", "smoke")] == 1.0

    def test_smoke_fire(self):
        assert CATEGORY_RELATIONSHIPS[("smoke", "fire")] == 0.8

    def test_fire_smoke_symmetric(self):
        score_a = CATEGORY_RELATIONSHIPS.get(("fire", "smoke"), CATEGORY_RELATIONSHIPS.get(("smoke", "fire"), 0.0))
        score_b = CATEGORY_RELATIONSHIPS.get(("smoke", "fire"), CATEGORY_RELATIONSHIPS.get(("fire", "smoke"), 0.0))
        assert score_a == score_b

    def test_noise_unrelated(self):
        score = semantic_score("noise", "fire", 0.0)
        assert score == 0.0


# ============================================================
# Signal Lifecycle State Machine
# ============================================================

class TestSignalState:
    def test_all_states_exist(self):
        assert SignalState.WATCH.value == "watch"
        assert SignalState.PROBABLE_HOTSPOT.value == "probable_hotspot"
        assert SignalState.HIGH_CONFIDENCE.value == "high_confidence"
        assert SignalState.ARCHIVED.value == "archived"

    def test_state_count(self):
        assert len(SignalState) == 4


# ============================================================
# Entity Construction
# ============================================================

class TestEntities:
    def test_observation_defaults(self):
        obs = Observation()
        assert obs.status == "submitted"
        assert obs.category == "other"
        assert obs.language == "en"

    def test_signal_defaults(self):
        sig = Signal()
        assert sig.state == SignalState.WATCH
        assert sig.version == 1
        assert sig.confidence.value == 0.0

    def test_interpretation_defaults(self):
        interp = Interpretation()
        assert interp.model == "gemini-2.0-flash"
        assert interp.prompt_version == "v3.2"
        assert interp.schema_version == "v2.1"

    def test_provider_record_defaults(self):
        pr = ProviderRecord()
        assert pr.status == "available"
        assert pr.confidence == 0.0
        assert pr.latency_ms == 0.0

    def test_audit_event_defaults(self):
        ae = AuditEvent()
        assert ae.policy_version == "2.0"
        assert ae.engine_version == "2.1.0"

    def test_signal_event_defaults(self):
        se = SignalEvent()
        assert se.event_type == ""
        assert se.policy_version == "2.0"
        assert se.engine_version == "2.1.0"

    def test_notification_defaults(self):
        n = Notification()
        assert n.channel == ""
        assert n.sent_at is None

    def test_media_defaults(self):
        m = __import__("app.domain.entities", fromlist=["Media"]).Media()
        assert m.media_type == ""
        assert m.size_bytes == 0

    def test_policy_version_defaults(self):
        pv = PolicyVersion()
        assert pv.is_active is False
        assert pv.version == ""
