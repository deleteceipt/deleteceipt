"""Report generator and HMAC-SHA256 signer for GDPR compliance assessments."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .engine import AssessmentResult, SectionScore
from .verticals import CROSS_FRAMEWORK

# ---------------------------------------------------------------------------
# Signing helpers
# ---------------------------------------------------------------------------

def _sign_payload(payload: dict, signing_key: str) -> str:
    """Return HMAC-SHA256 hex digest over canonical JSON of payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(
    result: AssessmentResult,
    org_id: str,
    signing_key: str,
    signing_key_id: str = "",
) -> dict:
    """
    Generate a signed compliance assessment artifact.

    Returns:
        {
          "payload": { ... },
          "signature": "<HMAC-SHA256 hex>",
          "signing_key_id": "<key_id>"   # omitted if signing_key_id is empty
        }
    """
    payload: dict = {
        "assessment_id": f"assess_{uuid.uuid4()}",
        "organization_id": org_id,
        "completed_at": datetime.now(tz=timezone.utc).isoformat(),
        "vertical": result.vertical,
        "overall_score": result.overall_score,
        "maturity_tier": result.maturity_tier,
        "section_scores": {
            sid: round(ss.pct, 2)
            for sid, ss in result.section_scores.items()
        },
        "critical_gaps": result.critical_gaps,
        "schema_version": "1.0",
    }

    signature = _sign_payload(payload, signing_key)

    artifact: dict = {
        "payload": payload,
        "signature": signature,
    }
    if signing_key_id:
        artifact["signing_key_id"] = signing_key_id

    return artifact


def verify_artifact(artifact: dict, signing_key: str) -> bool:
    """
    Verify HMAC-SHA256 over canonical JSON of artifact["payload"].

    Returns True if the signature is valid, False otherwise.
    """
    try:
        payload = artifact["payload"]
        stored_sig = artifact["signature"]
    except (KeyError, TypeError):
        return False

    expected = _sign_payload(payload, signing_key)
    return hmac.compare_digest(expected, stored_sig)


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

_TIER_DESCRIPTIONS = {
    "Foundational": "Critical gaps exist across multiple domains. Immediate remediation required.",
    "Developing": "Basic controls in place, but significant gaps remain. Structured programme needed.",
    "Advanced": "Solid compliance posture. Focus on automation and continuous monitoring.",
    "Exemplary": "Leading compliance posture. Maintain controls and update for emerging requirements.",
}

_RISK_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def render_text_report(result: AssessmentResult, artifact: dict) -> str:
    """
    Render a human-readable text report with:
    - Assessment metadata
    - Section scorecard
    - Gap analysis
    - Remediation roadmap
    """
    payload = artifact["payload"]
    lines: list[str] = []

    # Header
    lines += [
        "=" * 72,
        "GDPR COMPLIANCE ASSESSMENT REPORT",
        "=" * 72,
        f"Assessment ID : {payload['assessment_id']}",
        f"Organization  : {payload['organization_id']}",
        f"Completed At  : {payload['completed_at']}",
        f"Vertical      : {result.vertical}",
        f"Schema Version: {payload['schema_version']}",
        "",
        "-" * 72,
        "OVERALL SCORECARD",
        "-" * 72,
        f"Overall Score : {result.overall_score:.1f} / 100",
        f"Maturity Tier : {result.maturity_tier}",
        f"Assessment    : {_TIER_DESCRIPTIONS.get(result.maturity_tier, '')}",
        "",
        "-" * 72,
        "SECTION SCORES",
        "-" * 72,
    ]

    for section_id, ss in result.section_scores.items():
        bar_len = int(ss.pct / 5)  # 20-char bar
        bar = "#" * bar_len + "." * (20 - bar_len)
        flag = " [CRITICAL GAP]" if ss.is_critical_gap else ""
        lines.append(
            f"  {ss.title:<40s}  [{bar}]  {ss.pct:5.1f}%{flag}"
        )

    lines += [""]

    # Gap analysis
    if result.critical_gaps:
        lines += [
            "-" * 72,
            "CRITICAL GAP ANALYSIS",
            "-" * 72,
            "The following sections scored below the Documented threshold (25%):",
            "",
        ]
        for sid in result.critical_gaps:
            ss = result.section_scores[sid]
            lines.append(f"  {ss.title} ({sid})  —  score: {ss.pct:.1f}%")
            for cs in ss.controls_detail:
                if cs.maturity_level < 1 and cs.remediation:
                    lines.append(
                        f"    * {cs.remediation.gap_label}"
                        f"  [Risk: {cs.remediation.risk_level}]"
                        f"  [Effort: {cs.remediation.effort}]"
                    )
            lines.append("")

    # Remediation roadmap
    lines += [
        "-" * 72,
        "REMEDIATION ROADMAP",
        "-" * 72,
        "Priority ordering: Critical → High → Medium → Low",
        "",
    ]

    # Collect all remediation items
    items: list[tuple[str, str, str, str, str, Optional[str]]] = []
    for sid, ss in result.section_scores.items():
        for cs in ss.controls_detail:
            if cs.remediation and cs.maturity_level < 2:
                items.append((
                    cs.remediation.risk_level,
                    ss.title,
                    cs.label,
                    cs.remediation.gap_label,
                    cs.remediation.effort,
                    cs.remediation.open_source_component,
                ))

    items.sort(key=lambda x: _RISK_ORDER.get(x[0], 99))

    for risk, sec_title, ctrl_label, gap, effort, oss in items:
        lines.append(f"  [{risk:<8s}] {sec_title} — {ctrl_label}")
        lines.append(f"             Gap: {gap}  |  Effort: {effort}")
        if oss:
            lines.append(f"             Recommended tool: {oss}")
        lines.append("")

    # Cross-framework mappings
    framework_map = CROSS_FRAMEWORK.get(result.vertical, {})
    if framework_map:
        lines += [
            "-" * 72,
            f"CROSS-FRAMEWORK MAPPINGS ({result.vertical.upper()})",
            "-" * 72,
        ]
        for sid, frameworks in framework_map.items():
            ss = result.section_scores.get(sid)
            title = ss.title if ss else sid
            lines.append(f"  {title}: {', '.join(frameworks)}")
        lines.append("")

    # Signature block
    lines += [
        "-" * 72,
        "ARTIFACT INTEGRITY",
        "-" * 72,
        f"Signature (HMAC-SHA256): {artifact['signature']}",
    ]
    if "signing_key_id" in artifact:
        lines.append(f"Signing Key ID: {artifact['signing_key_id']}")
    lines += ["=" * 72, ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def render_html_report(
    result: AssessmentResult,
    artifact: dict,
    controls_by_section: dict,
) -> str:
    """
    Render an HTML compliance report.

    Args:
        result: AssessmentResult from the engine.
        artifact: Signed artifact from generate_report.
        controls_by_section: {section_id: SectionDef} from engine.sections.
    """
    payload = artifact["payload"]

    tier_color = {
        "Foundational": "#d32f2f",
        "Developing": "#f57c00",
        "Advanced": "#1976d2",
        "Exemplary": "#388e3c",
    }.get(result.maturity_tier, "#333")

    def pct_color(pct: float) -> str:
        if pct < 25:
            return "#d32f2f"
        if pct < 50:
            return "#f57c00"
        if pct < 75:
            return "#1976d2"
        return "#388e3c"

    # Section rows
    section_rows = ""
    for sid, ss in result.section_scores.items():
        gap_badge = (
            ' <span style="background:#d32f2f;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">CRITICAL GAP</span>'
            if ss.is_critical_gap
            else ""
        )
        section_rows += (
            f"<tr>"
            f"<td>{ss.title}{gap_badge}</td>"
            f"<td style='color:{pct_color(ss.pct)};font-weight:bold'>{ss.pct:.1f}%</td>"
            f"<td>"
            f"<div style='background:#eee;border-radius:4px;height:14px;width:200px;display:inline-block;vertical-align:middle;'>"
            f"<div style='background:{pct_color(ss.pct)};width:{ss.pct:.1f}%;height:100%;border-radius:4px;'></div>"
            f"</div>"
            f"</td>"
            f"</tr>"
        )

    # Remediation items
    items: list[tuple[str, str, str, str, str, Optional[str]]] = []
    for sid, ss in result.section_scores.items():
        for cs in ss.controls_detail:
            if cs.remediation and cs.maturity_level < 2:
                items.append((
                    cs.remediation.risk_level,
                    ss.title,
                    cs.label,
                    cs.remediation.gap_label,
                    cs.remediation.effort,
                    cs.remediation.open_source_component,
                ))
    items.sort(key=lambda x: _RISK_ORDER.get(x[0], 99))

    rem_rows = ""
    for risk, sec_title, ctrl_label, gap, effort, oss in items:
        risk_color = {"Critical": "#d32f2f", "High": "#f57c00", "Medium": "#1976d2", "Low": "#388e3c"}.get(risk, "#333")
        oss_cell = f'<a href="https://github.com/deleteceipt/deleteceipt">{oss}</a>' if oss == "deleteceipt" else (oss or "—")
        rem_rows += (
            f"<tr>"
            f"<td style='color:{risk_color};font-weight:bold'>{risk}</td>"
            f"<td>{sec_title}</td>"
            f"<td>{ctrl_label}</td>"
            f"<td>{gap}</td>"
            f"<td>{effort}</td>"
            f"<td>{oss_cell}</td>"
            f"</tr>"
        )

    sig_key_row = ""
    if "signing_key_id" in artifact:
        sig_key_row = f"<p><strong>Signing Key ID:</strong> {artifact['signing_key_id']}</p>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>GDPR Compliance Assessment Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 24px; color: #333; }}
  h1 {{ color: #1a237e; }}
  h2 {{ color: #283593; border-bottom: 2px solid #e8eaf6; padding-bottom: 6px; }}
  .meta {{ background: #f5f5f5; border-radius: 6px; padding: 16px; margin-bottom: 24px; }}
  .score-card {{ font-size: 2.5rem; font-weight: bold; color: {tier_color}; }}
  .tier {{ font-size: 1.2rem; color: {tier_color}; font-weight: bold; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
  th {{ background: #e8eaf6; text-align: left; padding: 8px 12px; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #eee; }}
  .sig {{ background: #f5f5f5; border-radius: 6px; padding: 16px; font-family: monospace; word-break: break-all; }}
</style>
</head>
<body>
<h1>GDPR Compliance Assessment Report</h1>
<div class="meta">
  <p><strong>Assessment ID:</strong> {payload['assessment_id']}</p>
  <p><strong>Organization:</strong> {payload['organization_id']}</p>
  <p><strong>Completed At:</strong> {payload['completed_at']}</p>
  <p><strong>Vertical:</strong> {result.vertical}</p>
  <p><strong>Schema Version:</strong> {payload['schema_version']}</p>
</div>

<h2>Overall Score</h2>
<p class="score-card">{result.overall_score:.1f}<span style="font-size:1.2rem"> / 100</span></p>
<p class="tier">{result.maturity_tier}</p>
<p>{_TIER_DESCRIPTIONS.get(result.maturity_tier, '')}</p>

<h2>Section Scores</h2>
<table>
  <thead><tr><th>Section</th><th>Score</th><th>Progress</th></tr></thead>
  <tbody>{section_rows}</tbody>
</table>

<h2>Remediation Roadmap</h2>
<table>
  <thead><tr><th>Risk</th><th>Section</th><th>Control</th><th>Gap</th><th>Effort</th><th>Tool</th></tr></thead>
  <tbody>{rem_rows}</tbody>
</table>

<h2>Artifact Integrity</h2>
<div class="sig">
  <p><strong>Signature (HMAC-SHA256):</strong><br/>{artifact['signature']}</p>
  {sig_key_row}
</div>
</body>
</html>"""

    return html
