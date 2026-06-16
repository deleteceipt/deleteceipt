from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from deleteceipt import compute_file_hash, issue_receipt, verify_receipt


KEY = "test-signing-key-do-not-use-in-production"

UPLOADED_AT = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
COMPLETED_AT = datetime(2026, 3, 1, 10, 0, 5, tzinfo=timezone.utc)
DELETED_AT = datetime(2026, 3, 1, 10, 0, 6, tzinfo=timezone.utc)

FILES = [
    {"path": "input/doc.pdf", "size_bytes": 4096, "role": "input"},
    {"path": "output/doc.docx", "size_bytes": 8192, "role": "output"},
]


def _make_receipt(job_id: str = "job-123", data: bytes = b"hello world") -> dict:
    fh = compute_file_hash(data)
    return issue_receipt(
        job_id=job_id,
        file_hash=fh,
        uploaded_at=UPLOADED_AT,
        processing_completed_at=COMPLETED_AT,
        deleted_at=DELETED_AT,
        signing_key=KEY,
        files_deleted=FILES,
    )


class TestComputeFileHash:
    def test_known_hash_correct(self):
        import hashlib
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert compute_file_hash(data) == expected

    def test_empty_bytes(self):
        import hashlib
        assert compute_file_hash(b"") == hashlib.sha256(b"").hexdigest()

    def test_different_data_different_hash(self):
        assert compute_file_hash(b"foo") != compute_file_hash(b"bar")


class TestIssueReceipt:
    def test_contains_required_fields(self):
        r = _make_receipt()
        for field in ("job_id", "file_hash_sha256", "uploaded_at", "processing_completed_at",
                      "deleted_at", "files_deleted", "server_signature"):
            assert field in r, f"Missing field: {field}"

    def test_job_id_matches(self):
        r = _make_receipt("job-xyz")
        assert r["job_id"] == "job-xyz"

    def test_files_deleted_preserved(self):
        r = _make_receipt()
        assert r["files_deleted"] == FILES

    def test_empty_files_deleted(self):
        fh = compute_file_hash(b"data")
        r = issue_receipt("j", fh, UPLOADED_AT, COMPLETED_AT, DELETED_AT, KEY)
        assert r["files_deleted"] == []

    def test_key_version_included_when_provided(self):
        fh = compute_file_hash(b"data")
        r = issue_receipt("j", fh, UPLOADED_AT, COMPLETED_AT, DELETED_AT, KEY, key_version="v2")
        assert r["key_version"] == "v2"

    def test_key_version_absent_when_not_provided(self):
        r = _make_receipt()
        assert "key_version" not in r

    def test_signature_is_base64(self):
        import base64
        r = _make_receipt()
        # Should not raise
        base64.b64decode(r["server_signature"])

    def test_deterministic_for_same_inputs(self):
        r1 = _make_receipt()
        r2 = _make_receipt()
        assert r1["server_signature"] == r2["server_signature"]

    def test_different_key_different_signature(self):
        fh = compute_file_hash(b"data")
        r1 = issue_receipt("j", fh, UPLOADED_AT, COMPLETED_AT, DELETED_AT, "key-one")
        r2 = issue_receipt("j", fh, UPLOADED_AT, COMPLETED_AT, DELETED_AT, "key-two")
        assert r1["server_signature"] != r2["server_signature"]


class TestVerifyReceipt:
    def test_valid_receipt_passes(self):
        r = _make_receipt()
        assert verify_receipt(r, KEY) is True

    def test_wrong_key_fails(self):
        r = _make_receipt()
        assert verify_receipt(r, "wrong-key") is False

    def test_tampered_job_id_fails(self):
        r = _make_receipt()
        r["job_id"] = "tampered"
        assert verify_receipt(r, KEY) is False

    def test_tampered_file_hash_fails(self):
        r = _make_receipt()
        r["file_hash_sha256"] = "a" * 64
        assert verify_receipt(r, KEY) is False

    def test_tampered_deleted_at_fails(self):
        r = _make_receipt()
        r["deleted_at"] = "2099-01-01T00:00:00+00:00"
        assert verify_receipt(r, KEY) is False

    def test_missing_signature_fails(self):
        r = _make_receipt()
        del r["server_signature"]
        assert verify_receipt(r, KEY) is False

    def test_bytes_key_works(self):
        fh = compute_file_hash(b"data")
        r = issue_receipt("j", fh, UPLOADED_AT, COMPLETED_AT, DELETED_AT, b"bytes-key")
        assert verify_receipt(r, b"bytes-key") is True

    def test_original_receipt_not_mutated(self):
        r = _make_receipt()
        original_sig = r["server_signature"]
        verify_receipt(r, KEY)
        assert r["server_signature"] == original_sig
