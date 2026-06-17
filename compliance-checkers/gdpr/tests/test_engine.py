"""Tests for checker.engine — scoring engine."""

from __future__ import annotations

import pytest
from pathlib import Path

from checker.engine import AssessmentEngine, SectionScore, AssessmentResult

CONTROLS_DIR = Path(__file__).parent.parent / "controls"


@pytest.fixture(scope="module")
def engine() -> AssessmentEngine:
    return AssessmentEngine(controls_dir=CONTROLS_DIR)


# ---------------------------------------------------------------------------
# Engine loading
# ---------------------------------------------------------------------------

class TestEngineLoading:
    def test_loads_all_14_sections(self, engine: AssessmentEngine):
        assert len(engine.sections) == 14

    def test_available_sections_returns_list(self, engine: AssessmentEngine):
        sections = engine.available_sections()
        assert isinstance(sections, list)
        assert len(sections) == 14

    def test_known_sections_present(self, engine: AssessmentEngine):
        sections = engine.available_sections()
        for expected in [
            "primary_storage",
            "search_indexes",
            "deletion_receipt_issuance",
            "cryptographic_erasure",
            "deletion_testing",
        ]:
            assert expected in sections, f"{expected!r} not found in sections"

    def test_each_section_has_controls(self, engine: AssessmentEngine):
        for sid, section in engine.sections.items():
            assert len(section.controls) >= 3, (
                f"Section {sid!r} has fewer than 3 controls"
            )

    def test_controls_have_required_fields(self, engine: AssessmentEngine):
        for sid, section in engine.sections.items():
            for ctrl in section.controls:
                assert ctrl.id, f"Control in {sid!r} missing id"
                assert ctrl.label, f"Control {ctrl.id!r} missing label"
                assert 0 < ctrl.weight <= 2.0, (
                    f"Control {ctrl.id!r} weight {ctrl.weight} out of range"
                )

    def test_invalid_controls_dir_raises(self):
        with pytest.raises(FileNotFoundError):
            AssessmentEngine(controls_dir=Path("/nonexistent/path/controls"))


# ---------------------------------------------------------------------------
# score_section
# ---------------------------------------------------------------------------

class TestScoreSection:
    def test_all_max_answers_yields_max_score(self, engine: AssessmentEngine):
        section_id = "primary_storage"
        section = engine.sections[section_id]
        answers = {ctrl.id: 4 for ctrl in section.controls}
        ss = engine.score_section(section_id, answers)
        assert ss.score == pytest.approx(4.0, abs=1e-6)
        assert ss.pct == pytest.approx(100.0, abs=1e-6)
        assert ss.max_score == 4.0

    def test_all_zero_answers_yields_zero_score(self, engine: AssessmentEngine):
        section_id = "primary_storage"
        section = engine.sections[section_id]
        answers = {ctrl.id: 0 for ctrl in section.controls}
        ss = engine.score_section(section_id, answers)
        assert ss.score == pytest.approx(0.0, abs=1e-6)
        assert ss.pct == pytest.approx(0.0, abs=1e-6)

    def test_mixed_answers_between_bounds(self, engine: AssessmentEngine):
        section_id = "primary_storage"
        section = engine.sections[section_id]
        answers = {ctrl.id: 2 for ctrl in section.controls}
        ss = engine.score_section(section_id, answers)
        assert 0.0 < ss.score < 4.0
        assert 0.0 < ss.pct < 100.0

    def test_empty_answers_yields_zero(self, engine: AssessmentEngine):
        ss = engine.score_section("primary_storage", {})
        assert ss.score == pytest.approx(0.0)
        assert ss.pct == pytest.approx(0.0)

    def test_partial_answers_treated_as_zero_for_missing(self, engine: AssessmentEngine):
        section_id = "primary_storage"
        section = engine.sections[section_id]
        first_ctrl = section.controls[0]
        ss_partial = engine.score_section(section_id, {first_ctrl.id: 4})
        ss_full_zero = engine.score_section(section_id, {ctrl.id: 0 for ctrl in section.controls})
        # Partial with one max answer > full zero
        assert ss_partial.pct > ss_full_zero.pct

    def test_section_score_returns_correct_type(self, engine: AssessmentEngine):
        ss = engine.score_section("search_indexes", {})
        assert isinstance(ss, SectionScore)

    def test_controls_detail_populated(self, engine: AssessmentEngine):
        section_id = "primary_storage"
        section = engine.sections[section_id]
        answers = {ctrl.id: 2 for ctrl in section.controls}
        ss = engine.score_section(section_id, answers)
        assert len(ss.controls_detail) == len(section.controls)

    def test_unknown_section_raises(self, engine: AssessmentEngine):
        with pytest.raises(ValueError, match="Unknown section"):
            engine.score_section("nonexistent_section", {})

    def test_invalid_maturity_level_raises(self, engine: AssessmentEngine):
        section = engine.sections["primary_storage"]
        ctrl = section.controls[0]
        with pytest.raises(ValueError, match="Maturity level"):
            engine.score_section("primary_storage", {ctrl.id: 5})

    def test_critical_gap_flag_when_low_score(self, engine: AssessmentEngine):
        ss = engine.score_section("primary_storage", {})
        assert ss.is_critical_gap is True

    def test_no_critical_gap_when_high_score(self, engine: AssessmentEngine):
        section = engine.sections["primary_storage"]
        answers = {ctrl.id: 4 for ctrl in section.controls}
        ss = engine.score_section("primary_storage", answers)
        assert ss.is_critical_gap is False

    def test_score_section_deletion_receipt_issuance(self, engine: AssessmentEngine):
        section_id = "deletion_receipt_issuance"
        section = engine.sections[section_id]
        answers = {ctrl.id: 3 for ctrl in section.controls}
        ss = engine.score_section(section_id, answers)
        assert ss.pct == pytest.approx(75.0, abs=1e-6)


# ---------------------------------------------------------------------------
# score_assessment
# ---------------------------------------------------------------------------

_CANNED_ALL_ZERO: dict[str, dict[str, int]] = {}
_CANNED_ALL_TWO: dict[str, dict[str, int]] = {}  # filled lazily


def _all_two_answers(engine: AssessmentEngine) -> dict[str, dict[str, int]]:
    return {
        sid: {ctrl.id: 2 for ctrl in section.controls}
        for sid, section in engine.sections.items()
    }


def _all_four_answers(engine: AssessmentEngine) -> dict[str, dict[str, int]]:
    return {
        sid: {ctrl.id: 4 for ctrl in section.controls}
        for sid, section in engine.sections.items()
    }


class TestScoreAssessment:
    def test_all_zero_gives_foundational_tier(self, engine: AssessmentEngine):
        result = engine.score_assessment({}, "general_saas")
        assert result.maturity_tier == "Foundational"
        assert result.overall_score == pytest.approx(0.0)

    def test_all_max_gives_exemplary_tier(self, engine: AssessmentEngine):
        answers = _all_four_answers(engine)
        result = engine.score_assessment(answers, "general_saas")
        assert result.maturity_tier == "Exemplary"
        assert result.overall_score == pytest.approx(100.0)

    def test_mid_score_gives_developing_or_advanced(self, engine: AssessmentEngine):
        answers = _all_two_answers(engine)
        result = engine.score_assessment(answers, "general_saas")
        assert result.maturity_tier in ("Developing", "Advanced")
        assert 40.0 < result.overall_score < 60.0

    def test_result_is_correct_type(self, engine: AssessmentEngine):
        result = engine.score_assessment({}, "healthcare")
        assert isinstance(result, AssessmentResult)

    def test_all_verticals_work(self, engine: AssessmentEngine):
        for vertical in ["general_saas", "healthcare", "financial_services", "legal_services", "public_sector_eu"]:
            result = engine.score_assessment({}, vertical)
            assert result.vertical == vertical
            assert 0.0 <= result.overall_score <= 100.0

    def test_critical_gaps_detected(self, engine: AssessmentEngine):
        result = engine.score_assessment({}, "general_saas")
        # All zero → all sections are critical gaps
        assert len(result.critical_gaps) == 14

    def test_critical_gaps_empty_when_all_max(self, engine: AssessmentEngine):
        answers = _all_four_answers(engine)
        result = engine.score_assessment(answers, "general_saas")
        assert result.critical_gaps == []

    def test_section_scores_all_present(self, engine: AssessmentEngine):
        result = engine.score_assessment({}, "general_saas")
        assert len(result.section_scores) == 14

    def test_invalid_vertical_raises(self, engine: AssessmentEngine):
        with pytest.raises(ValueError, match="Unknown vertical"):
            engine.score_assessment({}, "invalid_vertical")

    def test_healthcare_weights_applied(self, engine: AssessmentEngine):
        """Healthcare should produce a different score than general_saas for the same answers."""
        # Make deletion_receipt_issuance perfect, rest zero
        section = engine.sections["deletion_receipt_issuance"]
        answers = {"deletion_receipt_issuance": {ctrl.id: 4 for ctrl in section.controls}}
        result_saas = engine.score_assessment(answers, "general_saas")
        result_health = engine.score_assessment(answers, "healthcare")
        # Healthcare gives higher weight to deletion_receipt_issuance → higher overall score
        # (because the weighted contribution of the perfect section is larger)
        assert result_health.overall_score >= result_saas.overall_score

    def test_maturity_tier_thresholds(self, engine: AssessmentEngine):
        # Test threshold boundaries by controlling overall score via known inputs
        # Score exactly 0 → Foundational
        result = engine.score_assessment({}, "general_saas")
        assert result.maturity_tier == "Foundational"
        # Score 100 → Exemplary
        answers = _all_four_answers(engine)
        result = engine.score_assessment(answers, "general_saas")
        assert result.maturity_tier == "Exemplary"

    def test_partial_answers_valid(self, engine: AssessmentEngine):
        """Only some sections answered — the rest default to zero."""
        section = engine.sections["primary_storage"]
        answers = {"primary_storage": {ctrl.id: 4 for ctrl in section.controls}}
        result = engine.score_assessment(answers, "general_saas")
        assert result.overall_score > 0.0
        assert result.overall_score < 100.0
