"""Tests for domain policies — pure logic, no external dependencies."""

from app.domain.policies import (
    DuplicateConfig,
    composite_score,
    compute_similarity,
    environmental_score,
    independence_score,
    is_duplicate,
    semantic_score,
    spatial_score,
    temporal_score,
)


class TestDuplicateDetection:
    def test_exact_duplicate(self) -> None:
        assert is_duplicate(
            content_similarity=0.9,
            spatial_distance_meters=50.0,
            temporal_gap_minutes=5.0,
        )

    def test_different_content_not_duplicate(self) -> None:
        assert not is_duplicate(
            content_similarity=0.3,
            spatial_distance_meters=50.0,
            temporal_gap_minutes=5.0,
        )

    def test_distant_not_duplicate(self) -> None:
        assert not is_duplicate(
            content_similarity=0.9,
            spatial_distance_meters=300.0,
            temporal_gap_minutes=5.0,
        )

    def test_old_not_duplicate(self) -> None:
        assert not is_duplicate(
            content_similarity=0.9,
            spatial_distance_meters=50.0,
            temporal_gap_minutes=20.0,
        )


class TestSimilarityScoring:
    def test_identical_returns_high(self) -> None:
        s = compute_similarity(
            content_similarity=1.0,
            spatial_distance_meters=0.0,
            max_distance_meters=500.0,
            temporal_gap_minutes=0.0,
            max_window_minutes=30.0,
        )
        assert s == 1.0

    def test_distant_returns_low(self) -> None:
        s = compute_similarity(
            content_similarity=0.0,
            spatial_distance_meters=500.0,
            max_distance_meters=500.0,
            temporal_gap_minutes=30.0,
            max_window_minutes=30.0,
        )
        assert s == 0.0


class TestSemanticScore:
    def test_same_category(self) -> None:
        assert semantic_score("smoke", "smoke", evidence_overlap=1.0) == 1.0

    def test_related_category(self) -> None:
        score = semantic_score("smoke", "chemical", evidence_overlap=0.5)
        assert 0.5 < score < 0.7

    def test_unrelated_category(self) -> None:
        score = semantic_score("smoke", "noise", evidence_overlap=0.0)
        assert score == 0.0

    def test_other_category(self) -> None:
        score = semantic_score("smoke", "other", evidence_overlap=0.0)
        assert score == 0.1 * 0.6 + 0.4 * 0.0


class TestSpatialScore:
    def test_co_located(self) -> None:
        assert spatial_score(0.0) == 1.0

    def test_at_radius(self) -> None:
        assert spatial_score(500.0) == 0.0

    def test_beyond_radius(self) -> None:
        assert spatial_score(1000.0) == 0.0


class TestTemporalScore:
    def test_same_time(self) -> None:
        assert temporal_score(0.0) == 1.0

    def test_at_window(self) -> None:
        assert temporal_score(30.0) == 0.0


class TestIndependenceScore:
    def test_not_duplicate(self) -> None:
        assert independence_score(is_duplicate=False, same_device=False) == 1.0

    def test_duplicate(self) -> None:
        assert independence_score(is_duplicate=True, same_device=False) == 0.0

    def test_same_device_recent(self) -> None:
        assert independence_score(is_duplicate=False, same_device=True, same_session_minutes=3.0) == 0.2


class TestEnvironmentalScore:
    def test_neutral(self) -> None:
        assert environmental_score() == 0.0

    def test_fire_corroboration(self) -> None:
        score = environmental_score(firms_fire_detected=True)
        assert score == 0.25

    def test_rain_reduces(self) -> None:
        score = environmental_score(recent_precipitation=True)
        assert score == 0.0  # clamped from -0.2

    def test_multiple_factors(self) -> None:
        score = environmental_score(
            wind_consistent=True,
            low_humidity_high_temp=True,
            firms_fire_detected=True,
        )
        assert score == 0.5


class TestCompositeScore:
    def test_all_ones(self) -> None:
        s = composite_score(
            semantic=1.0, spatial=1.0, temporal=1.0, independence=1.0, environmental=1.0
        )
        assert s == 1.0

    def test_all_zeros(self) -> None:
        s = composite_score(
            semantic=0.0, spatial=0.0, temporal=0.0, independence=0.0, environmental=0.0
        )
        assert s == 0.0

    def test_clamped_to_1(self) -> None:
        s = composite_score(
            semantic=2.0, spatial=2.0, temporal=2.0, independence=2.0, environmental=2.0
        )
        assert s == 1.0

    def test_weighted_average(self) -> None:
        s = composite_score(
            semantic=1.0, spatial=0.0, temporal=0.0, independence=0.0, environmental=0.0
        )
        assert abs(s - 0.30) < 0.001
