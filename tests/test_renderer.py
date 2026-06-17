from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from deleteceipt import issue_receipt, compute_file_hash
from deleteceipt.enterprise import issue_enterprise_receipt
from deleteceipt.renderer import render_receipt

KEY = "renderer-test-key"
NOW = datetime(2025, 6, 17, 9, 0, 0, tzinfo=timezone.utc)


def _core_receipt() -> dict:
    fh = compute_file_hash(b"test document")
    return issue_receipt(
        job_id="job-render-test",
        file_hash=fh,
        uploaded_at=NOW,
        processing_completed_at=NOW,
        deleted_at=NOW,
        signing_key=KEY,
        files_deleted=[{"path": "/tmp/doc.pdf", "size_bytes": 1024, "role": "input"}],
    )


def _enterprise_receipt() -> dict:
    return issue_enterprise_receipt(
        user_id="usr-123",
        request_timestamp=NOW,
        data_categories=["contact_information", "uploaded_content"],
        storage_layers=["postgres:users", "s3:uploads"],
        retention_exceptions=["payment:stripe:legal:7yr"],
        signing_key=KEY,
        request_reference="DSR-001",
    )


class TestRenderCoreText:
    def test_contains_job_id(self):
        r = render_receipt(_core_receipt(), fmt="text")
        assert "job-render-test" in r

    def test_contains_deletion_receipt_header(self):
        r = render_receipt(_core_receipt(), fmt="text")
        assert "DELETION RECEIPT" in r

    def test_contains_file_fingerprint(self):
        receipt = _core_receipt()
        r = render_receipt(receipt, fmt="text")
        assert receipt["file_hash_sha256"][:20] in r

    def test_contains_verify_instructions(self):
        r = render_receipt(_core_receipt(), fmt="text")
        assert "verify" in r.lower()


class TestRenderCoreHTML:
    def test_is_valid_html(self):
        r = render_receipt(_core_receipt(), fmt="html")
        assert r.startswith("<!DOCTYPE html>")
        assert "</html>" in r

    def test_contains_job_id(self):
        receipt = _core_receipt()
        r = render_receipt(receipt, fmt="html")
        assert receipt["job_id"] in r

    def test_contains_signature(self):
        receipt = _core_receipt()
        r = render_receipt(receipt, fmt="html")
        assert receipt["server_signature"][:10] in r


class TestRenderEnterpriseText:
    def test_autodetects_enterprise(self):
        r = render_receipt(_enterprise_receipt(), fmt="text")
        assert "DELETION RECEIPT" in r

    def test_contains_user_id(self):
        r = render_receipt(_enterprise_receipt(), fmt="text")
        assert "usr-123" in r

    def test_contains_data_categories(self):
        r = render_receipt(_enterprise_receipt(), fmt="text")
        assert "contact_information" in r

    def test_contains_storage_layers(self):
        r = render_receipt(_enterprise_receipt(), fmt="text")
        assert "postgres:users" in r

    def test_contains_retention_exceptions(self):
        r = render_receipt(_enterprise_receipt(), fmt="text")
        assert "payment:stripe:legal:7yr" in r


class TestRenderJSON:
    def test_json_output_is_valid(self):
        receipt = _core_receipt()
        r = render_receipt(receipt, fmt="json")
        parsed = json.loads(r)
        assert parsed["job_id"] == receipt["job_id"]

    def test_enterprise_json_output(self):
        receipt = _enterprise_receipt()
        r = render_receipt(receipt, fmt="json")
        parsed = json.loads(r)
        assert "payload" in parsed
