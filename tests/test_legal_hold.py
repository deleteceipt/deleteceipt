from __future__ import annotations

import pytest

from deleteceipt.legal_hold import LegalHoldGate, InMemoryHoldStore


def _gate() -> LegalHoldGate:
    return LegalHoldGate(hold_store=InMemoryHoldStore())


class TestPlaceHold:
    def test_returns_hold_record(self):
        g = _gate()
        hold = g.place_hold("job-1", reason="Case 2025-CV-001")
        assert hold["job_id"] == "job-1"
        assert hold["reason"] == "Case 2025-CV-001"
        assert hold["active"] is True

    def test_placed_at_present(self):
        g = _gate()
        hold = g.place_hold("job-1", reason="test")
        assert "placed_at" in hold

    def test_reference_stored(self):
        g = _gate()
        hold = g.place_hold("job-1", reason="test", reference="TICKET-99")
        assert hold["reference"] == "TICKET-99"


class TestCheck:
    def test_no_hold_returns_false(self):
        g = _gate()
        result = g.check("job-1")
        assert result["held"] is False

    def test_held_job_returns_true(self):
        g = _gate()
        g.place_hold("job-1", reason="litigation")
        result = g.check("job-1")
        assert result["held"] is True

    def test_hold_notification_has_required_fields(self):
        g = _gate()
        g.place_hold("job-1", reason="litigation")
        n = g.check("job-1")["notification"]
        for field in ("type", "job_id", "reason", "placed_at", "checked_at", "message"):
            assert field in n, f"Missing field: {field}"

    def test_notification_type_is_hold_notification(self):
        g = _gate()
        g.place_hold("job-1", reason="test")
        assert g.check("job-1")["notification"]["type"] == "hold_notification"

    def test_different_job_not_held(self):
        g = _gate()
        g.place_hold("job-1", reason="test")
        assert g.check("job-2")["held"] is False


class TestReleaseHold:
    def test_release_clears_hold(self):
        g = _gate()
        g.place_hold("job-1", reason="test")
        g.release_hold("job-1")
        assert g.check("job-1")["held"] is False

    def test_release_returns_record(self):
        g = _gate()
        g.place_hold("job-1", reason="Case XYZ")
        record = g.release_hold("job-1")
        assert record["job_id"] == "job-1"
        assert record["original_reason"] == "Case XYZ"
        assert "released_at" in record

    def test_release_nonexistent_raises_key_error(self):
        g = _gate()
        with pytest.raises(KeyError):
            g.release_hold("no-such-job")


class TestAllHeld:
    def test_returns_held_job_ids(self):
        g = _gate()
        g.place_hold("job-1", reason="a")
        g.place_hold("job-2", reason="b")
        held = g.all_held()
        assert set(held) == {"job-1", "job-2"}

    def test_empty_when_no_holds(self):
        g = _gate()
        assert g.all_held() == []

    def test_released_job_not_in_all_held(self):
        g = _gate()
        g.place_hold("job-1", reason="test")
        g.release_hold("job-1")
        assert "job-1" not in g.all_held()
