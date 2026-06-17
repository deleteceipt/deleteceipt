from __future__ import annotations

from datetime import datetime, timezone

import pytest

from deleteceipt.enterprise import issue_enterprise_receipt, verify_enterprise_receipt

KEY = "enterprise-test-key-do-not-use"
NOW = datetime(2025, 6, 17, 9, 0, 0, tzinfo=timezone.utc)


def _make_receipt(**kwargs) -> dict:
    defaults = dict(
        user_id="usr-123",
        request_timestamp=NOW,
        data_categories=["contact_information", "uploaded_content"],
        storage_layers=["postgres:users", "s3:uploads"],
        signing_key=KEY,
    )
    defaults.update(kwargs)
    return issue_enterprise_receipt(**defaults)


class TestIssueEnterpriseReceipt:
    def test_has_payload_and_signature(self):
        r = _make_receipt()
        assert "payload" in r
        assert "signature" in r

    def test_payload_has_required_fields(self):
        r = _make_receipt()
        p = r["payload"]
        for field in (
            "receipt_id", "user_id", "request_timestamp", "deletion_timestamp",
            "data_categories", "storage_layers", "retention_exceptions",
            "initiated_by", "schema_version",
        ):
            assert field in p, f"Missing: {field}"

    def test_data_categories_sorted(self):
        r = _make_receipt(data_categories=["z_cat", "a_cat"])
        assert r["payload"]["data_categories"] == ["a_cat", "z_cat"]

    def test_storage_layers_sorted(self):
        r = _make_receipt(storage_layers=["z:store", "a:store"])
        assert r["payload"]["storage_layers"] == ["a:store", "z:store"]

    def test_retention_exceptions_default_empty(self):
        r = _make_receipt()
        assert r["payload"]["retention_exceptions"] == []

    def test_retention_exceptions_stored(self):
        r = _make_receipt(retention_exceptions=["payment:stripe:legal:7yr"])
        assert "payment:stripe:legal:7yr" in r["payload"]["retention_exceptions"]

    def test_initiated_by_default(self):
        r = _make_receipt()
        assert r["payload"]["initiated_by"] == "user_request"

    def test_signing_key_id_included_when_provided(self):
        r = _make_receipt(signing_key_id="key/v1")
        assert r["signing_key_id"] == "key/v1"

    def test_signing_key_id_absent_when_not_provided(self):
        r = _make_receipt()
        assert "signing_key_id" not in r

    def test_receipt_id_is_uuid(self):
        import uuid
        r = _make_receipt()
        uuid.UUID(r["payload"]["receipt_id"])  # should not raise

    def test_two_receipts_have_different_ids(self):
        r1 = _make_receipt()
        r2 = _make_receipt()
        assert r1["payload"]["receipt_id"] != r2["payload"]["receipt_id"]


class TestVerifyEnterpriseReceipt:
    def test_valid_receipt_passes(self):
        r = _make_receipt()
        assert verify_enterprise_receipt(r, KEY) is True

    def test_wrong_key_fails(self):
        r = _make_receipt()
        assert verify_enterprise_receipt(r, "wrong-key") is False

    def test_tampered_user_id_fails(self):
        r = _make_receipt()
        r["payload"]["user_id"] = "tampered"
        assert verify_enterprise_receipt(r, KEY) is False

    def test_tampered_storage_layer_fails(self):
        r = _make_receipt()
        r["payload"]["storage_layers"].append("fake:store")
        assert verify_enterprise_receipt(r, KEY) is False

    def test_missing_signature_fails(self):
        r = _make_receipt()
        del r["signature"]
        assert verify_enterprise_receipt(r, KEY) is False

    def test_missing_payload_fails(self):
        r = _make_receipt()
        del r["payload"]
        assert verify_enterprise_receipt(r, KEY) is False
