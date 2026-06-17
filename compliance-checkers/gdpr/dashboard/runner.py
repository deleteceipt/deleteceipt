"""Automated batch runner for GDPR compliance assessments.

Reads an operator.yaml config, runs the assessment engine, saves a signed
artifact, and exits with code 0 (pass) or 1 (fail) for CI gating.

Usage:
    python -m dashboard.runner --config operator.yaml --output assessments/
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from checker.engine import AssessmentEngine
from checker.report import generate_report
from .config import OperatorConfig, load_config


def run_assessment(config: OperatorConfig, output_dir: Path) -> dict:
    """
    Run a full GDPR compliance assessment from pre-configured answers.

    Args:
        config: Resolved OperatorConfig (signing key already present).
        output_dir: Directory where the signed artifact JSON will be saved.

    Returns:
        The signed artifact dict (payload + signature).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = AssessmentEngine()

    # Convert answers: config stores {section: {control: level}}
    # engine.score_assessment expects the same shape; ensure int values.
    all_answers: dict[str, dict[str, int]] = {}
    for section_id, controls in config.answers.items():
        all_answers[section_id] = {k: int(v) for k, v in controls.items()}

    result = engine.score_assessment(all_answers, config.vertical)

    artifact = generate_report(
        result,
        org_id=config.organization_id,
        signing_key=config.signing_key,
        signing_key_id=config.signing_key_id,
    )

    # Save artifact
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{config.organization_id}_{timestamp}.json"
    artifact_path = output_dir / filename
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    # Print summary table to stdout
    _print_summary(result, artifact, artifact_path)

    return artifact


def _print_summary(result, artifact, artifact_path: Path) -> None:
    """Print a compact summary table to stdout (no Rich dependency needed)."""
    payload = artifact["payload"]
    width = 72
    print("=" * width)
    print("GDPR COMPLIANCE ASSESSMENT — BATCH RUNNER SUMMARY")
    print("=" * width)
    print(f"  Organization : {payload['organization_id']}")
    print(f"  Vertical     : {payload['vertical']}")
    print(f"  Completed At : {payload['completed_at']}")
    print(f"  Overall Score: {result.overall_score:.1f} / 100")
    print(f"  Maturity Tier: {result.maturity_tier}")
    print(f"  Critical Gaps: {len(result.critical_gaps)}")
    print(f"  Artifact     : {artifact_path}")
    print("-" * width)
    print(f"  {'Section':<40s}  {'Score':>7s}  {'Status'}")
    print("-" * width)
    for sid, ss in result.section_scores.items():
        flag = "  [CRITICAL GAP]" if ss.is_critical_gap else ""
        print(f"  {ss.title:<40s}  {ss.pct:6.1f}%{flag}")
    print("=" * width)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GDPR compliance batch runner for CI/CD integration"
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to operator.yaml",
    )
    parser.add_argument(
        "--output",
        default=Path("assessments"),
        type=Path,
        help="Output directory for signed artifacts (default: assessments/)",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    artifact = run_assessment(config, args.output)

    overall_score = artifact["payload"]["overall_score"]
    if overall_score >= config.ci_threshold:
        print(
            f"\n[PASS] Score {overall_score:.1f} >= threshold {config.ci_threshold:.1f}"
        )
        return 0
    else:
        print(
            f"\n[FAIL] Score {overall_score:.1f} < threshold {config.ci_threshold:.1f}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
