"""Security Tests — Input validation, injection, boundary conditions.

Verifies the API layer rejects malformed/malicious input.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    ObservationCategoryEnum,
    ObservationSubmitRequest,
    SignalStateEnum,
)


class TestInputValidation:
    """ObservationSubmitRequest validation — the first line of defense."""

    def test_valid_request(self):
        req = ObservationSubmitRequest(
            content="Smoke visible", latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="device-1",
        )
        assert req.content == "Smoke visible"

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="", latitude=19.076, longitude=72.878,
                category="smoke", device_id="d1",
            )

    def test_content_too_long(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="x" * 5001, latitude=19.076, longitude=72.878,
                category="smoke", device_id="d1",
            )

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="Test", latitude=91.0, longitude=72.878,
                category="smoke", device_id="d1",
            )

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="Test", latitude=19.076, longitude=181.0,
                category="smoke", device_id="d1",
            )

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="Test", latitude=19.076, longitude=72.878,
                category="invalid_category", device_id="d1",
            )

    def test_invalid_language(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="Test", latitude=19.076, longitude=72.878,
                category="smoke", language="fr", device_id="d1",
            )

    def test_empty_device_id(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="Test", latitude=19.076, longitude=72.878,
                category="smoke", device_id="",
            )

    def test_device_id_too_long(self):
        with pytest.raises(ValidationError):
            ObservationSubmitRequest(
                content="Test", latitude=19.076, longitude=72.878,
                category="smoke", device_id="x" * 129,
            )

    def test_sql_injection_in_content(self):
        """SQL injection in content should be accepted (sanitized at API layer)."""
        req = ObservationSubmitRequest(
            content="'; DROP TABLE observations; --",
            latitude=19.076, longitude=72.878,
            category="smoke", device_id="d1",
        )
        assert "DROP" in req.content  # Accepted, sanitized at render time

    def test_xss_in_content(self):
        """XSS in content should be accepted (escaped at render time)."""
        req = ObservationSubmitRequest(
            content="<script>alert('xss')</script>",
            latitude=19.076, longitude=72.878,
            category="smoke", device_id="d1",
        )
        assert "<script>" in req.content  # Accepted, escaped at render time

    def test_path_traversal_in_device_id(self):
        """Path traversal in device_id should be accepted as string."""
        req = ObservationSubmitRequest(
            content="Test", latitude=19.076, longitude=72.878,
            category="smoke", device_id="../../../etc/passwd",
        )
        assert req.device_id == "../../../etc/passwd"


class TestEnumConstraints:
    """Verify all enum values are correct."""

    def test_signal_states(self):
        assert len(SignalStateEnum) == 4
        values = [s.value for s in SignalStateEnum]
        assert "watch" in values
        assert "probable_hotspot" in values
        assert "high_confidence" in values
        assert "archived" in values

    def test_observation_categories(self):
        assert len(ObservationCategoryEnum) == 10
        values = [c.value for c in ObservationCategoryEnum]
        assert "smoke" in values
        assert "fire" in values
        assert "other" in values

    def test_boundary_latitude(self):
        req = ObservationSubmitRequest(
            content="Test", latitude=90.0, longitude=0.0,
            category="smoke", device_id="d1",
        )
        assert req.latitude == 90.0

    def test_boundary_longitude(self):
        req = ObservationSubmitRequest(
            content="Test", latitude=0.0, longitude=180.0,
            category="smoke", device_id="d1",
        )
        assert req.longitude == 180.0


class TestDomainValidation:
    """Verify domain value objects reject invalid values."""

    def test_location_invalid_latitude(self):
        from app.domain.value_objects import Location
        with pytest.raises(ValueError):
            Location(91.0, 0.0)

    def test_location_invalid_longitude(self):
        from app.domain.value_objects import Location
        with pytest.raises(ValueError):
            Location(0.0, 181.0)

    def test_confidence_score_out_of_range(self):
        from app.domain.value_objects import ConfidenceScore
        with pytest.raises(ValueError):
            ConfidenceScore(-0.1)
        with pytest.raises(ValueError):
            ConfidenceScore(1.1)

    def test_fingerprint_deterministic(self):
        """Fingerprint is deterministic — same inputs always produce same hash."""
        from app.domain.value_objects import Location, ObservationFingerprint
        from datetime import datetime, timezone
        fp1 = ObservationFingerprint.compute(b"img", None, Location(19.0, 72.0), datetime.now(timezone.utc), "d1")
        fp2 = ObservationFingerprint.compute(b"img", None, Location(19.0, 72.0), datetime.now(timezone.utc), "d1")
        assert fp1.hash == fp2.hash

    def test_fingerprint_length(self):
        """SHA-256 produces 64-character hex string."""
        from app.domain.value_objects import Location, ObservationFingerprint
        from datetime import datetime, timezone
        fp = ObservationFingerprint.compute(b"img", None, Location(19.0, 72.0), datetime.now(timezone.utc), "d1")
        assert len(fp.hash) == 64
