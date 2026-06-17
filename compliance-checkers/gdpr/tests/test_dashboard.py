"""Tests for the dashboard package (runner + config loader).

The interactive Rich UI (app.py) is not tested here — it requires a live
terminal.  The runner and config modules are fully headless and CI-safe.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dashboard.config import OperatorConfig, load_config
from dashboard.runner import run_assessment

# Path to the example operator.yaml committed alongside the package
_OPERATOR_YAML = Path(__file__).parent.parent / "operator.yaml"
_LITERAL_KEY = "test-signing-key-abc123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config_with_literal_key() -> OperatorConfig:
    """Load operator.yaml but override the signing key with a literal value."""
    import yaml

    with open(_OPERATOR_YAML, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    return OperatorConfig(
        organization_id=data.get("organization_id", "test_org"),
        vertical=data.get("vertical", "general_saas"),
        signing_key=_LITERAL_KEY,
        signing_key_id=data.get("signing_key_id", ""),
        ci_threshold=float(data.get("ci_threshold", 50.0)),
        answers=data.get("answers", {}),
    )


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------

class TestRunnerLoadsConfig:
    def test_runner_loads_config(self):
        """Load the example operator.yaml with a literal signing key override."""
        config = _config_with_literal_key()
        assert config.organization_id == "org_example_hash"
        assert config.vertical == "general_saas"
        assert config.signing_key == _LITERAL_KEY
        assert config.ci_threshold == 50.0
        assert "primary_storage" in config.answers

    def test_config_signing_key_from_env(self, monkeypatch, tmp_path):
        """Env var resolution works when signing_key_env is set."""
        monkeypatch.setenv("GDPR_SIGNING_KEY", "env-resolved-secret")
        # operator.yaml uses signing_key_env: GDPR_SIGNING_KEY
        config = load_config(_OPERATOR_YAML)
        assert config.signing_key == "env-resolved-secret"

    def test_config_missing_key_raises(self, monkeypatch, tmp_path):
        """Missing signing key raises ValueError."""
        import yaml

        # Write a minimal config with no key or env var
        cfg_path = tmp_path / "nokey.yaml"
        cfg_path.write_text(
            "organization_id: org_test\nvertical: general_saas\nanswers: {}\n"
        )
        with pytest.raises(ValueError, match="No signing key"):
            load_config(cfg_path)


# ---------------------------------------------------------------------------
# Runner execution tests
# ---------------------------------------------------------------------------

class TestRunnerProducesArtifact:
    def test_runner_produces_artifact(self, tmp_path):
        """Full runner produces a dict with payload and signature."""
        config = _config_with_literal_key()
        artifact = run_assessment(config, tmp_path)

        assert "payload" in artifact
        assert "signature" in artifact
        payload = artifact["payload"]
        assert "overall_score" in payload
        assert "maturity_tier" in payload
        assert "section_scores" in payload
        assert payload["organization_id"] == "org_example_hash"

    def test_runner_saves_artifact_to_file(self, tmp_path):
        """Artifact is written as a JSON file in the output directory."""
        config = _config_with_literal_key()
        run_assessment(config, tmp_path)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1, f"Expected 1 JSON file, found: {json_files}"

        with open(json_files[0], "r", encoding="utf-8") as fh:
            loaded = json.load(fh)

        assert loaded["payload"]["organization_id"] == "org_example_hash"
        assert "signature" in loaded

    def test_runner_artifact_filename_format(self, tmp_path):
        """Artifact filename follows <org_id>_<timestamp>.json format."""
        config = _config_with_literal_key()
        run_assessment(config, tmp_path)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1
        name = json_files[0].name
        assert name.startswith("org_example_hash_")
        assert name.endswith(".json")

    def test_runner_creates_output_dir(self, tmp_path):
        """Output directory is created automatically if it does not exist."""
        nested = tmp_path / "a" / "b" / "c"
        assert not nested.exists()
        config = _config_with_literal_key()
        run_assessment(config, nested)
        assert nested.is_dir()
        assert any(nested.glob("*.json"))


# ---------------------------------------------------------------------------
# CI exit-code tests
# ---------------------------------------------------------------------------

class TestRunnerCIExitCode:
    def test_runner_ci_exit_code_pass(self, tmp_path):
        """Score above threshold -> overall_score >= threshold (runner returns artifact)."""
        # Build a config with all-4 answers so it always scores 100
        all_max_answers = {
            "primary_storage": {
                "hard_delete_implementation": 4,
                "soft_delete_pipeline": 4,
                "coverage_completeness": 4,
                "deletion_receipt_issuance": 4,
                "monitoring": 4,
            },
            "search_indexes": {
                "index_purge_on_delete": 4,
                "full_text_search_coverage": 4,
                "reindex_verification": 4,
                "derived_index_coverage": 4,
            },
            "cache_invalidation": {
                "cache_flush_on_delete": 4,
                "cache_ttl_policy": 4,
                "cdn_purge_capability": 4,
                "cache_inventory": 4,
            },
            "message_queues": {
                "queue_retention_bounded": 4,
                "event_tombstoning": 4,
                "consumer_notification": 4,
                "dead_letter_queue_purge": 4,
            },
            "backup_archive": {
                "backup_purge_procedure": 4,
                "backup_retention_policy": 4,
                "archive_cryptographic_erasure": 4,
                "backup_inventory": 4,
                "immutable_backup_controls": 4,
            },
            "logs_observability": {
                "log_pseudonymisation": 4,
                "log_retention_policy": 4,
                "trace_pii_scrubbing": 4,
                "metrics_no_pii": 4,
                "log_access_controls": 4,
            },
            "third_party_processors": {
                "dpa_deletion_clause": 4,
                "processor_deletion_confirmation": 4,
                "processor_inventory": 4,
                "processor_audit_rights": 4,
            },
            "ml_models": {
                "training_data_lineage": 4,
                "model_retraining_on_deletion": 4,
                "embedding_deletion": 4,
                "model_version_retention": 4,
                "differential_privacy_consideration": 4,
            },
            "deletion_receipt_issuance": {
                "receipt_issued_for_every_request": 4,
                "receipt_cryptographic_integrity": 4,
                "receipt_scope_documented": 4,
                "receipt_retention": 4,
                "receipt_verifiability": 4,
            },
            "audit_log_integrity": {
                "audit_log_for_all_deletions": 4,
                "audit_log_tamper_protection": 4,
                "audit_log_retention": 4,
                "audit_log_access_controls": 4,
            },
            "legal_hold_procedures": {
                "legal_hold_system": 4,
                "erasure_refusal_notification": 4,
                "hold_scope_minimisation": 4,
                "hold_release_procedure": 4,
                "hold_documentation": 4,
            },
            "federated_systems": {
                "federation_deletion_propagation": 4,
                "eventual_consistency_sla": 4,
                "cross_region_compliance": 4,
                "microservice_choreography": 4,
            },
            "cryptographic_erasure": {
                "per_user_encryption_keys": 4,
                "key_destruction_procedure": 4,
                "key_management_service": 4,
                "crypto_erasure_receipt": 4,
                "ciphertext_retained_acknowledged": 4,
            },
            "deletion_testing": {
                "automated_deletion_tests": 4,
                "periodic_deletion_drills": 4,
                "residual_data_scanning": 4,
                "deletion_sla_monitoring": 4,
                "test_coverage_documentation": 4,
            },
        }
        config = OperatorConfig(
            organization_id="passing_org",
            vertical="general_saas",
            signing_key=_LITERAL_KEY,
            signing_key_id="",
            ci_threshold=50.0,
            answers=all_max_answers,
        )
        artifact = run_assessment(config, tmp_path)
        score = artifact["payload"]["overall_score"]
        assert score >= config.ci_threshold, (
            f"Expected score >= {config.ci_threshold}, got {score}"
        )

    def test_runner_ci_exit_code_fail(self, tmp_path):
        """Score below threshold is detectable from the artifact."""
        config = OperatorConfig(
            organization_id="failing_org",
            vertical="general_saas",
            signing_key=_LITERAL_KEY,
            signing_key_id="",
            ci_threshold=99.0,   # near-impossible to reach
            answers={},           # all zeros
        )
        artifact = run_assessment(config, tmp_path)
        score = artifact["payload"]["overall_score"]
        assert score < config.ci_threshold, (
            f"Expected score < {config.ci_threshold}, got {score}"
        )

    def test_runner_main_returns_0_on_pass(self, tmp_path, monkeypatch):
        """runner.main() returns 0 when score >= threshold."""
        monkeypatch.setenv("GDPR_SIGNING_KEY", _LITERAL_KEY)
        from dashboard.runner import main as runner_main

        exit_code = runner_main([
            "--config", str(_OPERATOR_YAML),
            "--output", str(tmp_path),
        ])
        assert exit_code == 0

    def test_runner_main_returns_1_on_fail(self, tmp_path, monkeypatch):
        """runner.main() returns 1 when score < threshold."""
        import yaml

        # Write a config with all-zero answers and high threshold
        cfg_path = tmp_path / "fail.yaml"
        cfg_path.write_text(yaml.dump({
            "organization_id": "fail_org",
            "vertical": "general_saas",
            "signing_key": _LITERAL_KEY,
            "signing_key_id": "",
            "ci_threshold": 99.0,
            "answers": {},
        }))

        from dashboard.runner import main as runner_main

        exit_code = runner_main([
            "--config", str(cfg_path),
            "--output", str(tmp_path / "out"),
        ])
        assert exit_code == 1
