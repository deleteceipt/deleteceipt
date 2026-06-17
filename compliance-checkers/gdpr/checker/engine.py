"""Scoring engine: loads YAML control definitions and computes GDPR compliance scores."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .verticals import VERTICAL_WEIGHTS, VERTICALS

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RemediationDef:
    gap_label: str
    risk_level: str
    effort: str
    open_source_component: Optional[str]
    chapter_reference: str


@dataclass
class ControlDef:
    id: str
    label: str
    description: str
    weight: float
    remediation: RemediationDef


@dataclass
class SectionDef:
    section_id: str
    title: str
    source: str
    controls: list[ControlDef]

    def control_by_id(self, control_id: str) -> Optional[ControlDef]:
        for c in self.controls:
            if c.id == control_id:
                return c
        return None


@dataclass
class ControlScore:
    control_id: str
    label: str
    weight: float
    maturity_level: int  # 0-4
    weighted_score: float
    remediation: Optional[RemediationDef]


@dataclass
class SectionScore:
    section_id: str
    title: str
    score: float       # weighted average maturity, 0-4 scale
    max_score: float   # always 4.0
    pct: float         # 0-100
    controls_detail: list[ControlScore] = field(default_factory=list)

    @property
    def is_critical_gap(self) -> bool:
        """True if weighted score is effectively below 1.0 (None/Documented)."""
        return self.score < 1.0


@dataclass
class AssessmentResult:
    vertical: str
    section_scores: dict[str, SectionScore]
    overall_score: float   # 0-100
    maturity_tier: str
    critical_gaps: list[str]  # section_ids with score < 1.0 after weighting


# ---------------------------------------------------------------------------
# Maturity tiers
# ---------------------------------------------------------------------------

def _maturity_tier(pct: float) -> str:
    if pct < 25.0:
        return "Foundational"
    if pct < 50.0:
        return "Developing"
    if pct < 75.0:
        return "Advanced"
    return "Exemplary"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AssessmentEngine:
    """Loads YAML controls and scores GDPR compliance assessments."""

    DEFAULT_CONTROLS_DIR = Path(__file__).parent.parent / "controls"

    def __init__(self, controls_dir: Optional[Path] = None) -> None:
        self._controls_dir = Path(controls_dir) if controls_dir else self.DEFAULT_CONTROLS_DIR
        self.sections: dict[str, SectionDef] = {}
        self._load_controls()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_controls(self) -> None:
        """Load all YAML files from the controls directory."""
        yaml_files = sorted(self._controls_dir.glob("*.yaml"))
        if not yaml_files:
            raise FileNotFoundError(
                f"No YAML control files found in {self._controls_dir}"
            )
        for path in yaml_files:
            section = self._parse_section(path)
            self.sections[section.section_id] = section

    def _parse_section(self, path: Path) -> SectionDef:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        controls: list[ControlDef] = []
        for raw in data.get("controls", []):
            rem_raw = raw.get("remediation", {})
            remediation = RemediationDef(
                gap_label=rem_raw.get("gap_label", ""),
                risk_level=rem_raw.get("risk_level", ""),
                effort=rem_raw.get("effort", ""),
                open_source_component=rem_raw.get("open_source_component"),
                chapter_reference=rem_raw.get("chapter_reference", ""),
            )
            controls.append(
                ControlDef(
                    id=raw["id"],
                    label=raw["label"],
                    description=raw["description"],
                    weight=float(raw.get("weight", 1.0)),
                    remediation=remediation,
                )
            )

        return SectionDef(
            section_id=data["section"],
            title=data["title"],
            source=data["source"],
            controls=controls,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def available_sections(self) -> list[str]:
        """Return section IDs in definition order (sorted by YAML filename)."""
        return list(self.sections.keys())

    def score_section(self, section_id: str, answers: dict[str, int]) -> SectionScore:
        """
        Score a single section.

        Args:
            section_id: ID of the section to score.
            answers: Mapping of control_id → maturity_level (0-4).
                     Controls not present in answers are skipped.

        Returns:
            SectionScore with weighted average on the 0-4 scale.
        """
        section = self.sections.get(section_id)
        if section is None:
            raise ValueError(f"Unknown section: {section_id!r}")

        total_weight = 0.0
        weighted_sum = 0.0
        controls_detail: list[ControlScore] = []

        for ctrl in section.controls:
            if ctrl.id not in answers:
                # Unanswered controls are treated as 0 (no implementation)
                level = 0
            else:
                level = int(answers[ctrl.id])
                if not (0 <= level <= 4):
                    raise ValueError(
                        f"Maturity level must be 0-4, got {level} for {ctrl.id!r}"
                    )

            w_score = ctrl.weight * level
            total_weight += ctrl.weight
            weighted_sum += w_score

            controls_detail.append(
                ControlScore(
                    control_id=ctrl.id,
                    label=ctrl.label,
                    weight=ctrl.weight,
                    maturity_level=level,
                    weighted_score=w_score,
                    remediation=ctrl.remediation if level < 2 else None,
                )
            )

        if total_weight == 0.0:
            score = 0.0
        else:
            score = weighted_sum / total_weight  # 0-4 scale

        pct = (score / 4.0) * 100.0

        return SectionScore(
            section_id=section_id,
            title=section.title,
            score=round(score, 4),
            max_score=4.0,
            pct=round(pct, 2),
            controls_detail=controls_detail,
        )

    def score_assessment(
        self,
        all_answers: dict[str, dict[str, int]],
        vertical: str,
    ) -> AssessmentResult:
        """
        Score a full assessment across all sections for a given vertical.

        Args:
            all_answers: {section_id: {control_id: maturity_level (0-4)}}
            vertical: One of the defined vertical identifiers.

        Returns:
            AssessmentResult with weighted overall score and maturity tier.
        """
        if vertical not in VERTICALS:
            raise ValueError(
                f"Unknown vertical: {vertical!r}. Valid: {sorted(VERTICALS)}"
            )

        weights = VERTICAL_WEIGHTS[vertical]
        section_scores: dict[str, SectionScore] = {}

        for section_id in self.sections:
            answers = all_answers.get(section_id, {})
            sec_score = self.score_section(section_id, answers)
            section_scores[section_id] = sec_score

        # Compute weighted overall score (0-100)
        total_weight = 0.0
        weighted_sum = 0.0
        for section_id, sec_score in section_scores.items():
            w = weights.get(section_id, 1.0)
            total_weight += w
            weighted_sum += w * sec_score.pct

        overall_score = (weighted_sum / total_weight) if total_weight > 0.0 else 0.0
        overall_score = round(overall_score, 2)

        critical_gaps = [
            sid for sid, ss in section_scores.items() if ss.is_critical_gap
        ]

        return AssessmentResult(
            vertical=vertical,
            section_scores=section_scores,
            overall_score=overall_score,
            maturity_tier=_maturity_tier(overall_score),
            critical_gaps=critical_gaps,
        )
