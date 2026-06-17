"""Tests for checker.cli — CLI entry point."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from checker.cli import main
from checker.engine import AssessmentEngine
from checker.report import generate_report

CONTROLS_DIR = Path(__file__).parent.parent / "controls"
SIGNING_KEY = "cli-test-key-xyz789"
ORG_ID = "org_cli_test"


@pytest.fixture(scope="module")
def engine() -> AssessmentEngine:
    return AssessmentEngine(controls_dir=CONTROLS_DIR)


@pytest.fixture
def valid_artifact_file(engine: AssessmentEngine, tmp_path: Path) -> Path:
    result = engine.score_assessment({}, "general_saas")
    artifact = generate_report(result, ORG_ID, SIGNING_KEY)
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact))
    return path


class TestCLIVerify:
    def test_valid_artifact_returns_zero(self, valid_artifact_file: Path):
        rc = main(["verify", str(valid_artifact_file), "--key", SIGNING_KEY])
        assert rc == 0

    def test_wrong_key_returns_one(self, valid_artifact_file: Path):
        rc = main(["verify", str(valid_artifact_file), "--key", "wrong-key"])
        assert rc == 1

    def test_missing_file_returns_two(self, tmp_path: Path):
        rc = main(["verify", str(tmp_path / "does_not_exist.json"), "--key", SIGNING_KEY])
        assert rc == 2

    def test_key_env_var_works(self, valid_artifact_file: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_SIGNING_KEY", SIGNING_KEY)
        rc = main(["verify", str(valid_artifact_file), "--key-env", "TEST_SIGNING_KEY"])
        assert rc == 0

    def test_missing_key_env_var_returns_two(self, valid_artifact_file: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("NONEXISTENT_KEY_VAR", raising=False)
        rc = main(["verify", str(valid_artifact_file), "--key-env", "NONEXISTENT_KEY_VAR"])
        assert rc == 2

    def test_no_key_returns_nonzero(self, valid_artifact_file: Path, tmp_path: Path):
        """Omitting both --key and --key-env raises SystemExit (argparse mutually-exclusive required group)."""
        # argparse raises SystemExit(2) when a required mutually-exclusive group has no argument
        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(valid_artifact_file)])
        assert exc_info.value.code != 0

    def test_invalid_json_returns_two(self, tmp_path: Path):
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("not valid json {{{")
        rc = main(["verify", str(bad_json), "--key", SIGNING_KEY])
        assert rc == 2
