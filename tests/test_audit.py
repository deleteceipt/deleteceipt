from __future__ import annotations

import pytest

from deleteceipt.audit import AuditLog, InMemoryBackend


def _log_with_events(*event_types: str) -> AuditLog:
    log = AuditLog()
    for et in event_types:
        log.append_event(et, job_id="job-1", metadata={"filename": "doc.pdf"})
    return log


class TestAppendEvent:
    def test_returns_entry_with_seq(self):
        log = AuditLog()
        entry = log.append_event("upload", "job-1", {"filename": "doc.pdf"})
        assert entry["seq"] == 1

    def test_seq_increments(self):
        log = AuditLog()
        log.append_event("upload", "job-1", {})
        e2 = log.append_event("processing_start", "job-1", {})
        assert e2["seq"] == 2

    def test_entry_has_entry_hash(self):
        log = AuditLog()
        entry = log.append_event("upload", "job-1", {})
        assert "entry_hash" in entry
        assert len(entry["entry_hash"]) == 64

    def test_first_entry_prev_hash_is_genesis(self):
        log = AuditLog()
        entry = log.append_event("upload", "job-1", {})
        assert entry["prev_hash"] == "0" * 64

    def test_second_entry_prev_hash_matches_first(self):
        log = AuditLog()
        e1 = log.append_event("upload", "job-1", {})
        e2 = log.append_event("deleted", "job-1", {})
        assert e2["prev_hash"] == e1["entry_hash"]

    def test_event_type_stored(self):
        log = AuditLog()
        entry = log.append_event("download", "job-1", {})
        assert entry["event_type"] == "download"

    def test_job_id_stored(self):
        log = AuditLog()
        entry = log.append_event("upload", "job-abc", {})
        assert entry["job_id"] == "job-abc"

    def test_metadata_merged_into_entry(self):
        log = AuditLog()
        entry = log.append_event("upload", "job-1", {"filename": "report.pdf", "size_bytes": 1024})
        assert entry["filename"] == "report.pdf"
        assert entry["size_bytes"] == 1024

    def test_timestamp_present(self):
        log = AuditLog()
        entry = log.append_event("upload", "job-1", {})
        assert "timestamp" in entry


class TestVerifyChain:
    def test_empty_chain_is_valid(self):
        log = AuditLog()
        result = log.verify_chain()
        assert result["valid"] is True
        assert result["total_entries"] == 0

    def test_single_entry_valid(self):
        log = _log_with_events("upload")
        result = log.verify_chain()
        assert result["valid"] is True

    def test_multiple_entries_valid(self):
        log = _log_with_events("upload", "processing_start", "processing_complete", "deleted")
        result = log.verify_chain()
        assert result["valid"] is True
        assert result["total_entries"] == 4

    def test_tampered_entry_hash_detected(self):
        log = AuditLog()
        log.append_event("upload", "job-1", {})
        log.append_event("deleted", "job-1", {})
        # Directly tamper with the first stored entry
        log._backend._entries[0]["entry_hash"] = "a" * 64
        result = log.verify_chain()
        assert result["valid"] is False
        assert result["broken_at_seq"] == 1

    def test_tampered_payload_field_detected(self):
        log = AuditLog()
        log.append_event("upload", "job-1", {"filename": "real.pdf"})
        # Tamper with a payload field (hash won't match anymore)
        log._backend._entries[0]["filename"] = "malicious.exe"
        result = log.verify_chain()
        assert result["valid"] is False

    def test_broken_at_seq_points_to_tampered_entry(self):
        log = _log_with_events("upload", "processing_start", "deleted")
        log._backend._entries[1]["event_type"] = "tampered"
        result = log.verify_chain()
        assert result["broken_at_seq"] == 2

    def test_valid_chain_broken_at_seq_is_none(self):
        log = _log_with_events("upload", "deleted")
        result = log.verify_chain()
        assert result["broken_at_seq"] is None


class TestCustomBackend:
    def test_accepts_custom_backend(self):
        backend = InMemoryBackend()
        log = AuditLog(backend=backend)
        log.append_event("upload", "job-1", {})
        assert len(backend._entries) == 1
