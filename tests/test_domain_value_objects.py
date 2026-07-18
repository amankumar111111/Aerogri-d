"""Tests for domain value objects."""

from datetime import datetime, timezone

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


class TestLocation:
    def test_valid_location(self) -> None:
        loc = Location(latitude=19.0760, longitude=72.8777)
        assert loc.latitude == 19.0760
        assert loc.longitude == 72.8777

    def test_invalid_latitude_raises(self) -> None:
        try:
            Location(latitude=91.0, longitude=0.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_invalid_longitude_raises(self) -> None:
        try:
            Location(latitude=0.0, longitude=181.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_distance_to_self_is_zero(self) -> None:
        loc = Location(latitude=19.0760, longitude=72.8777)
        assert loc.distance_to(loc) == 0.0

    def test_distance_to_nearby(self) -> None:
        a = Location(latitude=19.0760, longitude=72.8777)
        b = Location(latitude=19.0770, longitude=72.8787)
        dist = a.distance_to(b)
        assert 100 < dist < 200  # roughly 150m

    def test_is_within(self) -> None:
        a = Location(latitude=19.0760, longitude=72.8777)
        b = Location(latitude=19.0761, longitude=72.8778)
        assert a.is_within(b, radius_meters=200)

    def test_grid_bucket(self) -> None:
        loc = Location(latitude=19.0760, longitude=72.8777)
        assert loc.grid_bucket() == "19.076,72.878"


class TestSeverity:
    def test_exceeds(self) -> None:
        low = Severity(level=SeverityLevel.LOW)
        high = Severity(level=SeverityLevel.HIGH)
        assert high.exceeds(low)
        assert not low.exceeds(high)


class TestEvidenceWeight:
    def test_government_weight(self) -> None:
        w = EvidenceWeight(source_type=SourceType.GOVERNMENT, reliability=0.9, freshness_hours=0.0)
        assert w.adjusted_weight() == 0.9

    def test_decay_over_time(self) -> None:
        w = EvidenceWeight(source_type=SourceType.CITIZEN, reliability=0.7, freshness_hours=14.0)
        adjusted = w.adjusted_weight()
        assert 0.3 < adjusted < 0.4  # ~50% decay after 14 hours


class TestConfidenceScore:
    def test_valid_score(self) -> None:
        s = ConfidenceScore(value=0.75)
        assert s.value == 0.75

    def test_invalid_score_raises(self) -> None:
        try:
            ConfidenceScore(value=1.5)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_classification_watch(self) -> None:
        s = ConfidenceScore(value=0.35)
        assert s.classification() == SignalState.WATCH

    def test_classification_probable_hotspot(self) -> None:
        s = ConfidenceScore(value=0.55)
        assert s.classification() == SignalState.PROBABLE_HOTSPOT

    def test_classification_high_confidence(self) -> None:
        s = ConfidenceScore(value=0.75)
        assert s.classification() == SignalState.HIGH_CONFIDENCE

    def test_classification_archived(self) -> None:
        s = ConfidenceScore(value=0.1)
        assert s.classification() == SignalState.ARCHIVED


class TestObservationFingerprint:
    def test_same_inputs_same_fingerprint(self) -> None:
        loc = Location(latitude=19.076, longitude=72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        a = ObservationFingerprint.compute(b"image", b"voice", loc, ts, "device-1")
        b = ObservationFingerprint.compute(b"image", b"voice", loc, ts, "device-1")
        assert a.hash == b.hash

    def test_different_device_different_fingerprint(self) -> None:
        loc = Location(latitude=19.076, longitude=72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        a = ObservationFingerprint.compute(b"image", b"voice", loc, ts, "device-1")
        b = ObservationFingerprint.compute(b"image", b"voice", loc, ts, "device-2")
        assert a.hash != b.hash

    def test_different_image_different_fingerprint(self) -> None:
        loc = Location(latitude=19.076, longitude=72.878)
        ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        a = ObservationFingerprint.compute(b"image1", b"voice", loc, ts, "device-1")
        b = ObservationFingerprint.compute(b"image2", b"voice", loc, ts, "device-1")
        assert a.hash != b.hash
