"""
Renders the filled-out Markdown compliance report for EU AI Act Article 14.
"""

from __future__ import annotations
from datetime import datetime
from checks import SECTION_TITLES, SUBSECTION_TITLES, ANNEX_III_SECTORS


STATUS_SYMBOL = {
    "compliant": "✓",
    "partial":   "~",
    "gap":       "✗",
    "skipped":   "-",
}

STATUS_LABEL = {
    "compliant": "Compliant",
    "partial":   "Partial",
    "gap":       "Gap",
    "skipped":   "Skipped",
}


def _md_escape(text: str) -> str:
    """Escape pipe characters so they don't break Markdown tables."""
    return text.replace("|", "\\|")


def _role_label(roles: list[str]) -> str:
    labels = {"provider": "Provider", "deployer": "Deployer"}
    return " / ".join(labels[r] for r in roles if r in labels)


def generate_report(
    *,
    system_name: str,
    operator_name: str,
    timestamp: datetime,
    roles: list[str],
    sectors: list[str],
    gate_answers: dict[str, str],
    results: list[dict],
    applicable_checks: list[dict],
) -> str:
    """
    Build and return the full Markdown report as a string.

    results is a list of dicts:
        {"check": <check dict>, "status": "compliant"|"partial"|"gap"|"skipped", "note": str}
    """
    lines: list[str] = []

    role_display = " / ".join(r.capitalize() for r in roles)
    sector_display = ", ".join(sectors) if sectors else "None selected"
    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    date_str = timestamp.strftime("%Y-%m-%d")

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        "# EU AI Act Article 14 — Human Oversight Compliance Report",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| System name | {_md_escape(system_name)} |",
        f"| Operator | {_md_escape(operator_name)} |",
        f"| Assessment date | {ts_str} |",
        f"| Role(s) assessed | {role_display} |",
        f"| Annex III sector(s) | {_md_escape(sector_display)} |",
        "",
    ]

    # ── Applicability gate ────────────────────────────────────────────────────
    lines += [
        "## Applicability Gate",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Is this system listed in Annex III of the EU AI Act? | {gate_answers.get('q1', '')} |",
        f"| Is it used in the EU or affects persons in the EU? | {gate_answers.get('q2', '')} |",
        f"| Is it classified as high-risk under Art. 6? | {gate_answers.get('q3', '')} |",
        "",
    ]

    # ── Per-section tables ────────────────────────────────────────────────────
    result_map = {r["check"]["id"]: r for r in results}

    seen_sections: list[str] = []
    seen_subsections: list[str] = []

    for section_key in ("A", "B", "C", "D", "E"):
        section_checks = [r for r in results if r["check"]["section"] == section_key]
        if not section_checks:
            continue

        section_title = SECTION_TITLES.get(section_key, f"Section {section_key}")
        lines += [f"## {section_title}", ""]

        # Group by subsection
        subsections_seen: list[str] = []
        for r in section_checks:
            sub = r["check"]["subsection"]
            if sub not in subsections_seen:
                subsections_seen.append(sub)

        for sub in subsections_seen:
            sub_title = SUBSECTION_TITLES.get(sub, sub)
            if sub != section_key:  # don't repeat heading for flat sections
                lines += [f"### {sub_title}", ""]

            lines += [
                "| Check ID | Requirement | Article | Status | Notes |",
                "|----------|-------------|---------|--------|-------|",
            ]
            for r in section_checks:
                if r["check"]["subsection"] != sub:
                    continue
                chk = r["check"]
                sym = STATUS_SYMBOL[r["status"]]
                note = _md_escape(r["note"] or "")
                req = _md_escape(chk["requirement"])
                lines.append(
                    f"| {chk['id']} | {req} | {chk['article']} | {sym} | {note} |"
                )
            lines.append("")

    # ── Tally ─────────────────────────────────────────────────────────────────
    tally = {"compliant": 0, "partial": 0, "gap": 0, "skipped": 0}
    for r in results:
        tally[r["status"]] += 1
    total = sum(tally.values())

    lines += [
        "## Tally",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| ✓ Compliant | {tally['compliant']} |",
        f"| ~ Partial | {tally['partial']} |",
        f"| ✗ Gap | {tally['gap']} |",
        f"| - Skipped | {tally['skipped']} |",
        f"| **Total assessed** | **{total}** |",
        "",
    ]

    # ── Overall status ────────────────────────────────────────────────────────
    non_skipped = total - tally["skipped"]
    if tally["gap"] == 0 and tally["partial"] == 0:
        overall = "**Compliant**"
    elif tally["gap"] == 0:
        overall = "**Conditionally compliant**"
    else:
        overall = "**Non-compliant**"

    lines += [
        "## Overall Compliance Status",
        "",
        f"Overall assessment: {overall}",
        "",
    ]

    # ── Remediation log ───────────────────────────────────────────────────────
    remediation = [r for r in results if r["status"] in ("gap", "partial")]
    if remediation:
        lines += [
            "## Remediation Log",
            "",
            "| Check ID | Status | Requirement | Notes |",
            "|----------|--------|-------------|-------|",
        ]
        for r in remediation:
            chk = r["check"]
            sym = STATUS_SYMBOL[r["status"]]
            note = _md_escape(r["note"] or "")
            req = _md_escape(chk["requirement"])
            lines.append(f"| {chk['id']} | {sym} | {req} | {note} |")
        lines.append("")
    else:
        lines += ["## Remediation Log", "", "_No gaps or partial items._", ""]

    # ── Evidence checklist ────────────────────────────────────────────────────
    non_compliant_checks = [r for r in results if r["status"] != "compliant"]
    if non_compliant_checks:
        lines += ["## Evidence Checklist", "", "_For items not marked compliant:_", ""]

        current_section = None
        for r in non_compliant_checks:
            chk = r["check"]
            sec = chk["section"]
            if sec != current_section:
                current_section = sec
                lines.append(f"**{SECTION_TITLES.get(sec, sec)}**")
                lines.append("")
            lines.append(f"- **{chk['id']}** ({STATUS_LABEL[r['status']]}): {chk['evidence']}")
        lines.append("")
    else:
        lines += ["## Evidence Checklist", "", "_All items compliant — no evidence gaps._", ""]

    # ── Caveats ───────────────────────────────────────────────────────────────
    lines += [
        "## Caveats",
        "",
        "1. This checklist covers Art. 14 human oversight requirements only. "
           "Full EU AI Act compliance requires assessment of Arts. 9–15, 17, 26, "
           "and Annexes I–IV, among others.",
        "2. This tool is not a substitute for legal advice. The EU AI Act is "
           "subject to ongoing regulatory guidance and Member State implementation.",
        "3. Applicability of specific provisions (e.g., Art. 14(5) biometric "
           "requirements) depends on your system's classification and use case. "
           "Seek qualified legal and technical counsel.",
        "4. 'Compliant' answers are self-assessed declarations. They do not "
           "constitute a conformity assessment or notified body certification.",
        "5. This report should be reviewed and updated whenever the system, its "
           "deployment context, or applicable regulations change materially.",
        "",
    ]

    # ── Legal disclaimer ──────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "_This report was generated by an automated compliance checker tool and "
        "constitutes a self-assessment only. It does not constitute legal advice, "
        "a conformity assessment, or a certification of compliance with the EU AI Act "
        "or any other applicable law._",
        "",
    ]

    return "\n".join(lines)


def write_report(content: str, timestamp: datetime) -> str:
    """Write the report to a timestamped file in CWD. Returns the file path."""
    import os
    filename = f"report_{timestamp.strftime('%Y-%m-%d_%H%M%S')}.md"
    path = os.path.join(os.getcwd(), filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path
