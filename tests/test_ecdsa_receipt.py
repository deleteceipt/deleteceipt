"""Tests for ECDSA deletion receipts (P-256 / secp256r1)."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import pytest

from deleteceipt.ecdsa_receipt import (
    generate_keypair,
    issue_receipt_ecdsa,
    verify_receipt_ecdsa,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UPLOADED_AT = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
COMPLETED_AT = datetime(2026, 3, 1, 10, 0, 5, tzinfo=timezone.utc)
DELETED_AT = datetime(2026, 3, 1, 10, 0, 6, tzinfo=timezone.utc)

FILES = [
    {"path": "input/doc.pdf", "size_bytes": 4096, "role": "input"},
    {"path": "output/doc.docx", "size_bytes": 8192, "role": "output"},
]

FILE_HASH = "a" * 64  # placeholder hex digest


@pytest.fixture(scope="module")
def keypair() -> tuple[str, str]:
    return generate_keypair()


@pytest.fixture(scope="module")
def receipt(keypair: tuple[str, str]) -> dict:
    priv, _ = keypair
    return issue_receipt_ecdsa(
        job_id="job-ecdsa-1",
        file_hash=FILE_HASH,
        uploaded_at=UPLOADED_AT,
        processing_completed_at=COMPLETED_AT,
        deleted_at=DELETED_AT,
        private_key_pem=priv,
        files_deleted=FILES,
    )


# ---------------------------------------------------------------------------
# generate_keypair
# ---------------------------------------------------------------------------

class TestGenerateKeypair:
    def test_returns_two_strings(self, keypair):
        priv, pub = keypair
        assert isinstance(priv, str)
        assert isinstance(pub, str)

    def test_private_key_is_pem(self, keypair):
        priv, _ = keypair
        assert "PRIVATE KEY" in priv

    def test_public_key_is_pem(self, keypair):
        _, pub = keypair
        assert "PUBLIC KEY" in pub

    def test_different_calls_yield_different_keys(self):
        priv1, pub1 = generate_keypair()
        priv2, pub2 = generate_keypair()
        assert priv1 != priv2
        assert pub1 != pub2


# ---------------------------------------------------------------------------
# issue_receipt_ecdsa
# ---------------------------------------------------------------------------

class TestIssueReceiptEcdsa:
    def test_contains_required_fields(self, receipt):
        for field in (
            "job_id",
            "file_hash_sha256",
            "uploaded_at",
            "processing_completed_at",
            "deleted_at",
            "files_deleted",
            "server_signature_ecdsa",
            "signing_public_key_pem",
        ):
            assert field in receipt, f"Missing field: {field}"

    def test_job_id_matches(self, receipt):
        assert receipt["job_id"] == "job-ecdsa-1"

    def test_file_hash_matches(self, receipt):
        assert receipt["file_hash_sha256"] == FILE_HASH

    def test_files_deleted_preserved(self, receipt):
        assert receipt["files_deleted"] == FILES

    def test_signature_is_base64(self, receipt):
        # Should not raise
        base64.b64decode(receipt["server_signature_ecdsa"])

    def test_public_key_embedded_in_receipt(self, receipt, keypair):
        _, expected_pub = keypair
        assert receipt["signing_public_key_pem"] == expected_pub

    def test_key_version_included_when_provided(self, keypair):
        priv, _ = keypair
        r = issue_receipt_ecdsa(
            "j", FILE_HASH, UPLOADED_AT, COMPLETED_AT, DELETED_AT,
            priv, key_version="v3",
        )
        assert r["key_version"] == "v3"

    def test_key_version_absent_when_not_provided(self, receipt):
        assert "key_version" not in receipt

    def test_empty_files_deleted_defaults_to_empty_list(self, keypair):
        priv, _ = keypair
        r = issue_receipt_ecdsa(
            "j", FILE_HASH, UPLOADED_AT, COMPLETED_AT, DELETED_AT, priv
        )
        assert r["files_deleted"] == []

    def test_different_keypairs_different_signatures(self):
        priv1, _ = generate_keypair()
        priv2, _ = generate_keypair()
        r1 = issue_receipt_ecdsa("j", FILE_HASH, UPLOADED_AT, COMPLETED_AT, DELETED_AT, priv1)
        r2 = issue_receipt_ecdsa("j", FILE_HASH, UPLOADED_AT, COMPLETED_AT, DELETED_AT, priv2)
        assert r1["server_signature_ecdsa"] != r2["server_signature_ecdsa"]


# ---------------------------------------------------------------------------
# verify_receipt_ecdsa
# ---------------------------------------------------------------------------

class TestVerifyReceiptEcdsa:
    def test_valid_receipt_passes(self, receipt):
        assert verify_receipt_ecdsa(receipt) is True

    def test_valid_with_explicit_public_key(self, receipt, keypair):
        _, pub = keypair
        assert verify_receipt_ecdsa(receipt, public_key_pem=pub) is True

    def test_wrong_public_key_fails(self, receipt):
        _, wrong_pub = generate_keypair()
        assert verify_receipt_ecdsa(receipt, public_key_pem=wrong_pub) is False

    def test_tampered_job_id_fails(self, receipt):
        r = dict(receipt)
        r["job_id"] = "tampered-id"
        assert verify_receipt_ecdsa(r) is False

    def test_tampered_file_hash_fails(self, receipt):
        r = dict(receipt)
        r["file_hash_sha256"] = "b" * 64
        assert verify_receipt_ecdsa(r) is False

    def test_tampered_deleted_at_fails(self, receipt):
        r = dict(receipt)
        r["deleted_at"] = "2099-01-01T00:00:00+00:00"
        assert verify_receipt_ecdsa(r) is False

    def test_missing_signature_fails(self, receipt):
        r = dict(receipt)
        del r["server_signature_ecdsa"]
        assert verify_receipt_ecdsa(r) is False

    def test_original_receipt_not_mutated(self, receipt):
        sig_before = receipt["server_signature_ecdsa"]
        pub_before = receipt["signing_public_key_pem"]
        verify_receipt_ecdsa(receipt)
        assert receipt["server_signature_ecdsa"] == sig_before
        assert receipt["signing_public_key_pem"] == pub_before

    def test_self_contained_verification_no_key_arg(self, receipt):
        """Public key embedded in receipt is sufficient for verification."""
        assert verify_receipt_ecdsa(receipt, public_key_pem=None) is True

    def test_corrupted_base64_signature_fails(self, receipt):
        r = dict(receipt)
        r["server_signature_ecdsa"] = "not-valid-base64!!!"
        assert verify_receipt_ecdsa(r) is False
