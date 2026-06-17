"""Tests for checker.report — report generation and signature verification."""

from __future__ import annotations

import copy
import json
import pytest
from pathlib import Path

from checker.engine import AssessmentEngine, AssessmentResult
from checker.report import generate_report, verify_artifact, render_text_report, render_html_report

CONTROLS_DIR = Path(__file__).parent.parent / "controls"
SIGNING_KEY = "test-signing-key-abc123"
SIGNING_KEY_ID = "key-v1"
ORG_ID = "org_abc123"


@pytest.fixture(scope="module")
def engine() -> AssessmentEngine:
    return AssessmentEngine(controls_dir=CONTROLS_DIR)


@pytest.fixture(scope="module")
def zero_result(engine: AssessmentEngine) -> AssessmentResult:
    return engine.score_assessment({}, "general_saas")


@pytest.fixture(scope="module")
def full_result(engine: AssessmentEngine) -> AssessmentResult:
    answers = {
        sid: {ctrl.id: 4 for ctrl in section.controls}
        for sid, section in engine.sections.items()
    }
    return engine.score_assessment(answers, "healthcare")


@pytest.fixture(scope="module")
def zero_artifact(zero_result: AssessmentResult) -> dict:
    return generate_report(zero_result, ORG_ID, SIGNING_KEY, SIGNING_KEY_ID)


@pytest.fixture(scope="module")
def full_artifact(full_result: AssessmentResult) -> dict:
    return generate_report(full_result, ORG_ID, SIGNING_KEY)


# ---------------------------------------------------------------------------
# generate_report structure
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_returns_dict(self, zero_artifact: dict):
        assert isinstance(zero_artifact, dict)

    def test_has_payload_key(self, zero_artifact: dict):
        assert "payload" in zero_artifact

    def test_has_signature_key(self, zero_artifact: dict):
        assert "signature" in zero_artifact

    def test_signature_is_hex_string(self, zero_artifact: dict):
        sig = zero_artifact["signature"]
        assert isinstance(sig, str)
        assert len(sig) == 64  # HMAC-SHA256 = 32 bytes = 64 hex chars
        int(sig, 16)  # must be valid hex

    def test_payload_has_assessment_id(self, zero_artifact: dict):
        assert "assessment_id" in zero_artifact["payload"]
        assert zero_artifact["payload"]["assessment_id"].startswith("assess_")

    def test_payload_has_organization_id(self, zero_artifact: dict):
        assert zero_artifact["payload"]["organization_id"] == ORG_ID

    def test_payload_has_completed_at(self, zero_artifact: dict):
        assert "completed_at" in zero_artifact["payload"]

    def test_payload_has_vertical(self, zero_artifact: dict):
        assert zero_artifact["payload"]["vertical"] == "general_saas"

    def test_payload_has_overall_score(self, zero_artifact: dict):
        assert "overall_score" in zero_artifact["payload"]
        assert zero_artifact["payload"]["overall_score"] == 0.0

    def test_payload_has_maturity_tier(self, zero_artifact: dict):
        assert zero_artifact["payload"]["maturity_tier"] == "Foundational"

    def test_payload_has_section_scores(self, zero_artifact: dict):
        section_scores = zero_artifact["payload"]["section_scores"]
        assert isinstance(section_scores, dict)
        assert len(section_scores) == 14

    def test_payload_has_critical_gaps(self, zero_artifact: dict):
        assert "critical_gaps" in zero_artifact["payload"]
        assert isinstance(zero_artifact["payload"]["critical_gaps"], list)

    def test_payload_has_schema_version(self, zero_artifact: dict):
        assert zero_artifact["payload"]["schema_version"] == "1.0"

    def test_signing_key_id_included_when_provided(self, zero_artifact: dict):
        assert "signing_key_id" in zero_artifact
        assert zero_artifact["signing_key_id"] == SIGNING_KEY_ID

    def test_signing_key_id_omitted_when_empty(self, full_artifact: dict):
        assert "signing_key_id" not in full_artifact

    def test_full_result_score_100(self, full_artifact: dict):
        assert full_artifact["payload"]["overall_score"] == pytest.approx(100.0)
        assert full_artifact["payload"]["maturity_tier"] == "Exemplary"

    def test_each_call_produces_unique_assessment_id(
        self, zero_result: AssessmentResult
    ):
        a1 = generate_report(zero_result, ORG_ID, SIGNING_KEY)
        a2 = generate_report(zero_result, ORG_ID, SIGNING_KEY)
        assert a1["payload"]["assessment_id"] != a2["payload"]["assessment_id"]


# ---------------------------------------------------------------------------
# verify_artifact
# ---------------------------------------------------------------------------

class TestVerifyArtifact:
    def test_valid_artifact_returns_true(self, zero_artifact: dict):
        assert verify_artifact(zero_artifact, SIGNING_KEY) is True

    def test_wrong_key_returns_false(self, zero_artifact: dict):
        assert verify_artifact(zero_artifact, "wrong-key") is False

    def test_tampered_payload_returns_false(self, zero_artifact: dict):
        tampered = copy.deepcopy(zero_artifact)
        tampered["payload"]["overall_score"] = 99.9
        assert verify_artifact(tampered, SIGNING_KEY) is False

    def test_tampered_organization_returns_false(self, zero_artifact: dict):
        tampered = copy.deepcopy(zero_artifact)
        tampered["payload"]["organization_id"] = "evil_org"
        assert verify_artifact(tampered, SIGNING_KEY) is False

    def test_empty_dict_returns_false(self):
        assert verify_artifact({}, SIGNING_KEY) is False

    def test_missing_signature_returns_false(self, zero_artifact: dict):
        no_sig = {k: v for k, v in zero_artifact.items() if k != "signature"}
        assert verify_artifact(no_sig, SIGNING_KEY) is False

    def test_full_artifact_verifies(self, full_artifact: dict):
        assert verify_artifact(full_artifact, SIGNING_KEY) is True

    def test_artifact_is_json_serializable(self, zero_artifact: dict):
        # Should be serializable and re-verifiable
        json_str = json.dumps(zero_artifact)
        loaded = json.loads(json_str)
        assert verify_artifact(loaded, SIGNING_KEY) is True


# ---------------------------------------------------------------------------
# render_text_report
# ---------------------------------------------------------------------------

class TestRenderTextReport:
    def test_returns_string(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert isinstance(text, str)
        assert len(text) > 100

    def test_contains_assessment_id(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert zero_artifact["payload"]["assessment_id"] in text

    def test_contains_maturity_tier(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert "Foundational" in text

    def test_contains_overall_score(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert "0.0" in text

    def test_contains_section_scores(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert "Primary Storage Deletion" in text

    def test_contains_critical_gap_label(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert "CRITICAL GAP" in text

    def test_contains_remediation_roadmap(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert "REMEDIATION ROADMAP" in text

    def test_contains_signature(self, zero_result: AssessmentResult, zero_artifact: dict):
        text = render_text_report(zero_result, zero_artifact)
        assert zero_artifact["signature"] in text

    def test_exemplary_report_no_critical_gaps(
        self, full_result: AssessmentResult, full_artifact: dict
    ):
        text = render_text_report(full_result, full_artifact)
        assert "Exemplary" in text
        # No critical gap sections in Exemplary report
        assert "CRITICAL GAP" not in text


# ---------------------------------------------------------------------------
# render_html_report
# ---------------------------------------------------------------------------

class TestRenderHtmlReport:
    def test_returns_string(self, zero_result: AssessmentResult, zero_artifact: dict, engine: AssessmentEngine):
        html = render_html_report(zero_result, zero_artifact, engine.sections)
        assert isinstance(html, str)

    def test_contains_doctype(self, zero_result: AssessmentResult, zero_artifact: dict, engine: AssessmentEngine):
        html = render_html_report(zero_result, zero_artifact, engine.sections)
        assert "<!DOCTYPE html>" in html

    def test_contains_overall_score(self, zero_result: AssessmentResult, zero_artifact: dict, engine: AssessmentEngine):
        html = render_html_report(zero_result, zero_artifact, engine.sections)
        assert "0.0" in html

    def test_contains_maturity_tier(self, zero_result: AssessmentResult, zero_artifact: dict, engine: AssessmentEngine):
        html = render_html_report(zero_result, zero_artifact, engine.sections)
        assert "Foundational" in html
