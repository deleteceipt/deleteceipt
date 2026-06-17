"""Interactive terminal dashboard for the GDPR compliance checker.

Modes:
    --interactive   Guided questionnaire through all 14 sections
    --view <file>   Display a previously saved artifact
    --summary       Show all artifacts in the assessments/ directory

Usage:
    python -m dashboard.app --interactive
    python -m dashboard.app --view assessments/org_20260101T120000Z.json
    python -m dashboard.app --view assessments/org_20260101T120000Z.json --key mysecret
    python -m dashboard.app --summary
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich import box

# Project imports
from checker.engine import AssessmentEngine
from checker.report import generate_report, verify_artifact

_ASSESSMENTS_DIR = Path(__file__).parent.parent / "assessments"

_MATURITY_LABELS = {
    0: "None / Ad-hoc",
    1: "Documented",
    2: "Implemented",
    3: "Tested",
    4: "Monitored / Automated",
}

_TIER_COLORS = {
    "Foundational": "red",
    "Developing": "yellow",
    "Advanced": "blue",
    "Exemplary": "green",
}


def _score_color(pct: float) -> str:
    if pct < 25:
        return "red"
    if pct < 50:
        return "yellow"
    if pct < 75:
        return "blue"
    return "green"


# ---------------------------------------------------------------------------
# Mode A: Interactive guided questionnaire
# ---------------------------------------------------------------------------

def run_interactive(console: Console) -> None:
    """Guided step-by-step questionnaire through all 14 GDPR sections."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]GDPR Right-to-Erasure Compliance Checker[/bold cyan]\n"
            "[dim]Interactive Assessment Questionnaire[/dim]\n\n"
            f"[dim]Date: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}[/dim]",
            box=box.DOUBLE,
        )
    )
    console.print()

    engine = AssessmentEngine()
    sections = engine.available_sections()

    # Pick vertical
    console.print("[bold]Select industry vertical:[/bold]")
    verticals = [
        "general_saas",
        "healthcare",
        "financial_services",
        "legal_services",
        "public_sector_eu",
    ]
    for i, v in enumerate(verticals, 1):
        console.print(f"  [{i}] {v}")
    v_idx = IntPrompt.ask("  Enter number", default=1, console=console) - 1
    v_idx = max(0, min(v_idx, len(verticals) - 1))
    vertical = verticals[v_idx]
    console.print()

    org_id = Prompt.ask("  Organization ID (or press Enter for 'interactive_session')",
                        default="interactive_session", console=console)
    signing_key = Prompt.ask("  Signing key (HMAC secret)",
                             default="dev-key", console=console)
    signing_key_id = Prompt.ask("  Signing key ID (optional)", default="", console=console)
    console.print()

    all_answers: dict[str, dict[str, int]] = {}

    for idx, section_id in enumerate(sections, 1):
        sec_def = engine.sections[section_id]
        console.print(
            Panel(
                f"[bold]{idx}/{len(sections)}: {sec_def.title}[/bold]\n"
                f"[dim]Source: {sec_def.source}[/dim]",
                style="cyan",
            )
        )

        answers: dict[str, int] = {}
        for ctrl in sec_def.controls:
            console.print(f"\n  [bold]{ctrl.label}[/bold]")
            console.print(f"  [dim]{ctrl.description}[/dim]")
            console.print(
                "  [0] None  [1] Documented  [2] Implemented  [3] Tested  [4] Monitored"
            )
            level = IntPrompt.ask("  > ", default=0, console=console)
            level = max(0, min(level, 4))
            answers[ctrl.id] = level

        all_answers[section_id] = answers
        console.print()

    # Score and display
    result = engine.score_assessment(all_answers, vertical)
    artifact = generate_report(result, org_id, signing_key, signing_key_id)

    _display_scorecard(console, result, artifact)

    # Save artifact
    _ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = _ASSESSMENTS_DIR / f"{org_id}_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    console.print(f"\n[green]Artifact saved:[/green] {out_path}")
    console.print(
        f"\n[dim]Verify with:[/dim]  verify-assessment {out_path} --key <secret>"
    )


# ---------------------------------------------------------------------------
# Mode B: Results viewer
# ---------------------------------------------------------------------------

def run_viewer(console: Console, artifact_path: Path, key: str | None) -> None:
    """Load and display a previously saved artifact."""
    with open(artifact_path, "r", encoding="utf-8") as fh:
        artifact = json.load(fh)

    payload = artifact.get("payload", {})

    # Verify signature if key provided
    if key:
        valid = verify_artifact(artifact, key)
        sig_status = "[green]VALID[/green]" if valid else "[red]INVALID[/red]"
    else:
        sig_status = "[yellow]NOT CHECKED (no key provided)[/yellow]"

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]GDPR Compliance Assessment Report[/bold cyan]\n\n"
            f"  Assessment ID : {payload.get('assessment_id', 'n/a')}\n"
            f"  Organization  : {payload.get('organization_id', 'n/a')}\n"
            f"  Completed At  : {payload.get('completed_at', 'n/a')}\n"
            f"  Vertical      : {payload.get('vertical', 'n/a')}\n"
            f"  Signature     : {sig_status}",
            box=box.ROUNDED,
        )
    )

    # Score summary
    overall = payload.get("overall_score", 0.0)
    tier = payload.get("maturity_tier", "Unknown")
    color = _TIER_COLORS.get(tier, "white")

    console.print()
    console.print(
        f"  Overall Score: [{color}][bold]{overall:.1f} / 100[/bold][/{color}]   "
        f"Tier: [{color}]{tier}[/{color}]"
    )
    console.print()

    # Section scorecard
    table = Table(title="Section Scores", box=box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("Section", style="bold", min_width=38)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Bar", min_width=22)
    table.add_column("Status", min_width=14)

    section_scores = payload.get("section_scores", {})
    critical_gaps = set(payload.get("critical_gaps", []))

    for sid, pct in section_scores.items():
        bar_filled = int(pct / 5)
        bar = "[" + "#" * bar_filled + "." * (20 - bar_filled) + "]"
        c = _score_color(pct)
        status = "[red]CRITICAL GAP[/red]" if sid in critical_gaps else "[green]OK[/green]"
        table.add_row(sid, f"[{c}]{pct:.1f}%[/{c}]", f"[{c}]{bar}[/{c}]", status)

    console.print(table)

    if critical_gaps:
        console.print(f"\n[red]Critical gaps ({len(critical_gaps)}):[/red]")
        for sid in critical_gaps:
            console.print(f"  - {sid}")

    console.print(
        f"\n[dim]Signature:[/dim] {artifact.get('signature', 'n/a')[:32]}..."
    )
    if "signing_key_id" in artifact:
        console.print(f"[dim]Key ID:[/dim] {artifact['signing_key_id']}")


# ---------------------------------------------------------------------------
# Mode C: Summary dashboard
# ---------------------------------------------------------------------------

def run_summary(console: Console) -> None:
    """Load all artifacts from assessments/ and display a summary table."""
    _ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = sorted(_ASSESSMENTS_DIR.glob("*.json"))

    if not artifacts:
        console.print("[yellow]No assessment artifacts found in assessments/[/yellow]")
        return

    console.print()
    table = Table(
        title=f"Assessment History ({len(artifacts)} records)",
        box=box.SIMPLE_HEAVY,
        show_lines=True,
    )
    table.add_column("Date", min_width=20)
    table.add_column("Organization", min_width=24)
    table.add_column("Vertical", min_width=18)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Tier", min_width=14)
    table.add_column("Critical Gaps", justify="right", min_width=14)

    scores_by_org: dict[str, list[float]] = {}

    for path in artifacts:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                art = json.load(fh)
            p = art.get("payload", {})
            org = p.get("organization_id", "unknown")
            score = p.get("overall_score", 0.0)
            tier = p.get("maturity_tier", "Unknown")
            vertical = p.get("vertical", "unknown")
            completed = p.get("completed_at", "")[:10]
            gaps = len(p.get("critical_gaps", []))
            color = _score_color(score)
            tier_color = _TIER_COLORS.get(tier, "white")
            table.add_row(
                completed,
                org,
                vertical,
                f"[{color}]{score:.1f}[/{color}]",
                f"[{tier_color}]{tier}[/{tier_color}]",
                str(gaps),
            )
            scores_by_org.setdefault(org, []).append(score)
        except Exception as exc:
            table.add_row(path.name, "[red]parse error[/red]", "", "", "", "")

    console.print(table)

    # Trend analysis
    multi = {org: scores for org, scores in scores_by_org.items() if len(scores) > 1}
    if multi:
        console.print("\n[bold]Score Trends[/bold]")
        for org, scores in multi.items():
            delta = scores[-1] - scores[0]
            arrow = "[green]+[/green]" if delta > 0 else ("[red][/red]" if delta < 0 else "=")
            console.print(
                f"  {org}: {scores[0]:.1f} -> {scores[-1]:.1f}  ({arrow}{abs(delta):.1f})"
            )


# ---------------------------------------------------------------------------
# Shared: scorecard display
# ---------------------------------------------------------------------------

def _display_scorecard(console: Console, result, artifact: dict) -> None:
    payload = artifact["payload"]
    overall = result.overall_score
    tier = result.maturity_tier
    color = _TIER_COLORS.get(tier, "white")

    console.print()
    console.print(
        Panel.fit(
            f"[bold]Overall Score:[/bold] [{color}][bold]{overall:.1f} / 100[/bold][/{color}]\n"
            f"[bold]Maturity Tier:[/bold] [{color}]{tier}[/{color}]",
            title="Assessment Complete",
            box=box.ROUNDED,
        )
    )

    table = Table(title="Section Scorecard", box=box.SIMPLE_HEAVY)
    table.add_column("Section", style="bold", min_width=38)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Bar", min_width=22)

    for sid, ss in result.section_scores.items():
        bar_filled = int(ss.pct / 5)
        bar = "[" + "#" * bar_filled + "." * (20 - bar_filled) + "]"
        c = _score_color(ss.pct)
        label = ss.title
        if ss.is_critical_gap:
            label += " [red]*[/red]"
        table.add_row(label, f"[{c}]{ss.pct:.1f}%[/{c}]", f"[{c}]{bar}[/{c}]")

    console.print(table)

    if result.critical_gaps:
        console.print(f"[red]* Critical gap (score < 25%)[/red]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="GDPR Compliance Checker — Terminal Dashboard"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--interactive", action="store_true",
                      help="Run interactive guided questionnaire")
    mode.add_argument("--view", type=Path, metavar="ARTIFACT",
                      help="View a previously saved artifact")
    mode.add_argument("--summary", action="store_true",
                      help="Show summary of all saved artifacts")

    parser.add_argument("--key", default=None,
                        help="Signing key for signature verification (--view mode)")
    parser.add_argument("--key-env", default=None, metavar="ENV_VAR",
                        help="Env var name containing the signing key (--view mode)")

    args = parser.parse_args(argv)

    console = Console()

    # Resolve key for --view
    key: str | None = None
    if args.view:
        if args.key:
            key = args.key
        elif args.key_env:
            key = os.environ.get(args.key_env)

    if args.interactive:
        run_interactive(console)
    elif args.view:
        run_viewer(console, args.view, key)
    elif args.summary:
        run_summary(console)


if __name__ == "__main__":
    main()
