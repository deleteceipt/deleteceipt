"""Tests for the deleteceipt CLI.

These tests drive the CLI at the argparse / function level (via
``deleteceipt.cli.main()``) so they run without subprocess overhead and work
regardless of whether the ``deleteceipt`` console script is installed in the
current environment.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from deleteceipt.cli import main
from deleteceipt.receipt import compute_file_hash, issue_receipt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UPLOADED_AT = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
COMPLETED_AT = datetime(2026, 3, 1, 10, 0, 5, tzinfo=timezone.utc)
DELETED_AT = datetime(2026, 3, 1, 10, 0, 6, tzinfo=timezone.utc)
HMAC_KEY = "cli-test-key"


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def _make_hmac_receipt() -> dict:
    fh = compute_file_hash(b"cli test data")
    return issue_receipt(
        job_id="cli-job-1",
        file_hash=fh,
        uploaded_at=UPLOADED_AT,
        processing_completed_at=COMPLETED_AT,
        deleted_at=DELETED_AT,
        signing_key=HMAC_KEY,
        files_deleted=[{"path": "input/x.pdf", "size_bytes": 100, "role": "input"}],
    )


def _make_ecdsa_receipt() -> tuple[dict, str, str]:
    from deleteceipt.ecdsa_receipt import generate_keypair, issue_receipt_ecdsa
    priv, pub = generate_keypair()
    fh = compute_file_hash(b"cli ecdsa test")
    r = issue_receipt_ecdsa(
        job_id="cli-job-ecdsa",
        file_hash=fh,
        uploaded_at=UPLOADED_AT,
        processing_completed_at=COMPLETED_AT,
        deleted_at=DELETED_AT,
        private_key_pem=priv,
    )
    return r, priv, pub


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

class TestCLIVerify:
    def test_valid_receipt_exits_0(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(rfile), "--key", HMAC_KEY])
        assert exc_info.value.code == 0

    def test_valid_receipt_prints_ok(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit):
            main(["verify", str(rfile), "--key", HMAC_KEY])
        out = capsys.readouterr().out
        assert "OK" in out

    def test_wrong_key_exits_1(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(rfile), "--key", "wrong-key"])
        assert exc_info.value.code == 1

    def test_tampered_receipt_exits_1(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        receipt["job_id"] = "tampered"
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(rfile), "--key", HMAC_KEY])
        assert exc_info.value.code == 1

    def test_missing_file_exits_1(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(tmp_path / "nonexistent.json"), "--key", HMAC_KEY])
        assert exc_info.value.code == 1

    def test_invalid_json_exits_1(self, tmp_path, capsys):
        rfile = tmp_path / "bad.json"
        rfile.write_text("not json {{{")
        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(rfile), "--key", HMAC_KEY])
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# verify-ecdsa
# ---------------------------------------------------------------------------

class TestCLIVerifyEcdsa:
    def test_valid_receipt_exits_0(self, tmp_path, capsys):
        receipt, _, _ = _make_ecdsa_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify-ecdsa", str(rfile)])
        assert exc_info.value.code == 0

    def test_valid_receipt_prints_ok(self, tmp_path, capsys):
        receipt, _, _ = _make_ecdsa_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit):
            main(["verify-ecdsa", str(rfile)])
        assert "OK" in capsys.readouterr().out

    def test_tampered_payload_exits_1(self, tmp_path, capsys):
        receipt, _, _ = _make_ecdsa_receipt()
        receipt["job_id"] = "tampered"
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify-ecdsa", str(rfile)])
        assert exc_info.value.code == 1

    def test_explicit_pub_key_file(self, tmp_path, capsys):
        receipt, _, pub = _make_ecdsa_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)
        kfile = tmp_path / "pub.pem"
        kfile.write_text(pub)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify-ecdsa", str(rfile), "--key", str(kfile)])
        assert exc_info.value.code == 0

    def test_wrong_pub_key_file_exits_1(self, tmp_path, capsys):
        receipt, _, _ = _make_ecdsa_receipt()
        _, wrong_pub = __import__("deleteceipt.ecdsa_receipt", fromlist=["generate_keypair"]).generate_keypair()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)
        kfile = tmp_path / "wrong_pub.pem"
        kfile.write_text(wrong_pub)

        with pytest.raises(SystemExit) as exc_info:
            main(["verify-ecdsa", str(rfile), "--key", str(kfile)])
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# keygen
# ---------------------------------------------------------------------------

class TestCLIKeygen:
    def test_exits_0(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["keygen"])
        assert exc_info.value.code == 0

    def test_prints_private_key_marker(self, capsys):
        with pytest.raises(SystemExit):
            main(["keygen"])
        out = capsys.readouterr().out
        assert "PRIVATE KEY" in out

    def test_prints_public_key_marker(self, capsys):
        with pytest.raises(SystemExit):
            main(["keygen"])
        out = capsys.readouterr().out
        assert "PUBLIC KEY" in out

    def test_output_contains_two_pem_blocks(self, capsys):
        with pytest.raises(SystemExit):
            main(["keygen"])
        out = capsys.readouterr().out
        assert out.count("-----BEGIN") == 2
        assert out.count("-----END") == 2


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

class TestCLIInspect:
    def test_exits_0(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["inspect", str(rfile)])
        assert exc_info.value.code == 0

    def test_prints_job_id(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit):
            main(["inspect", str(rfile)])
        out = capsys.readouterr().out
        assert "job_id" in out
        assert "cli-job-1" in out

    def test_prints_file_hash(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit):
            main(["inspect", str(rfile)])
        out = capsys.readouterr().out
        assert "file_hash_sha256" in out

    def test_prints_deleted_at(self, tmp_path, capsys):
        receipt = _make_hmac_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit):
            main(["inspect", str(rfile)])
        out = capsys.readouterr().out
        assert "deleted_at" in out

    def test_works_with_ecdsa_receipt(self, tmp_path, capsys):
        receipt, _, _ = _make_ecdsa_receipt()
        rfile = tmp_path / "receipt.json"
        _write_json(rfile, receipt)

        with pytest.raises(SystemExit) as exc_info:
            main(["inspect", str(rfile)])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "signing_public_key_pem" in out
