#!/usr/bin/env python3
"""
EU AI Act Article 14 — Human Oversight Compliance Checker
Run: python checker.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from checks import CHECKS, ANNEX_III_SECTORS, SECTION_TITLES
from reporter import generate_report, write_report


# ── Terminal helpers ──────────────────────────────────────────────────────────

BOLD  = "\033[1m"
DIM   = "\033[2m"
CYAN  = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED   = "\033[31m"
RESET = "\033[0m"

def bold(s: str) -> str:   return f"{BOLD}{s}{RESET}"
def cyan(s: str) -> str:   return f"{CYAN}{s}{RESET}"
def green(s: str) -> str:  return f"{GREEN}{s}{RESET}"
def yellow(s: str) -> str: return f"{YELLOW}{s}{RESET}"
def red(s: str) -> str:    return f"{RED}{s}{RESET}"
def dim(s: str) -> str:    return f"{DIM}{s}{RESET}"


def hr(char: str = "─", width: int = 72) -> None:
    print(dim(char * width))


def ask_yes_no(prompt: str) -> bool:
    """Prompt until user enters y/yes or n/no (case-insensitive)."""
    while True:
        try:
            raw = input(f"  {prompt} [y/n]: ").strip().lower()
        except EOFError:
            sys.exit(0)
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please enter y or n.")


def ask_status(check_id: str) -> str:
    """Return 'compliant', 'partial', 'gap', or 'skipped'."""
    prompt = (
        f"  {bold('[x]')} Compliant  "
        f"{bold('[~]')} Partial  "
        f"{bold('[ ]')} Gap  "
        f"{bold('[s]')} Skip"
        f"\n  Your answer (x / ~ / n / s): "
    )
    while True:
        try:
            raw = input(prompt).strip().lower()
        except EOFError:
            sys.exit(0)
        if raw in ("x",):
            return "compliant"
        if raw in ("~",):
            return "partial"
        if raw in ("n", " "):
            return "gap"
        if raw in ("s",):
            return "skipped"
        print("  Invalid — enter x, ~, n, or s.")


def ask_note() -> str:
    """Optionally capture a short note."""
    try:
        raw = input("  Note (press Enter to skip): ").strip()
    except EOFError:
        return ""
    return raw


def ask_text(prompt: str, required: bool = True) -> str:
    while True:
        try:
            raw = input(f"  {prompt}: ").strip()
        except EOFError:
            sys.exit(0)
        if raw or not required:
            return raw
        print("  This field is required.")


def multi_select(options: list[str], prompt: str) -> list[int]:
    """
    Display a numbered list; user enters comma-separated numbers or 'none'.
    Returns list of 0-based indices.
    """
    for i, opt in enumerate(options, 1):
        print(f"    {i:2}. {opt}")
    print()
    while True:
        try:
            raw = input(f"  {prompt} (comma-separated numbers, or 0 for none): ").strip()
        except EOFError:
            sys.exit(0)
        if raw == "0" or raw.lower() == "none":
            return []
        parts = [p.strip() for p in raw.split(",")]
        try:
            indices = [int(p) - 1 for p in parts if p]
            if all(0 <= i < len(options) for i in indices):
                return list(dict.fromkeys(indices))  # deduplicate, preserve order
        except ValueError:
            pass
        print(f"  Enter numbers between 1 and {len(options)}, separated by commas.")


def role_select() -> list[str]:
    """Return list of applicable roles."""
    print()
    print("  1. Provider  (you place the system on the market or put it into service)")
    print("  2. Deployer  (you use the system under your own authority)")
    print("  3. Both")
    print()
    while True:
        try:
            raw = input("  Select role [1/2/3]: ").strip()
        except EOFError:
            sys.exit(0)
        if raw == "1":
            return ["provider"]
        if raw == "2":
            return ["deployer"]
        if raw == "3":
            return ["provider", "deployer"]
        print("  Enter 1, 2, or 3.")


# ── Main flow ─────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        _run()
    except KeyboardInterrupt:
        print(f"\n\n{yellow('Assessment cancelled.')} No report was written.")
        sys.exit(0)


def _run() -> None:
    print()
    hr("═")
    print(bold("  EU AI Act Article 14 — Human Oversight Compliance Checker"))
    hr("═")
    print("""
  This tool walks you through every Art. 14 check for a high-risk AI system,
  collects your self-assessed status for each item, and produces a filled-out
  Markdown compliance report.

  For each check you will be asked:
    x  = Compliant      (evidence exists and measure is in place)
    ~  = Partial        (partially implemented; remediation needed)
    n  = Gap            (not implemented; remediation required)
    s  = Skip           (not applicable to your specific context)

  Press Ctrl+C at any time to exit without saving.
""")
    hr()

    # ── Collect system / operator metadata ────────────────────────────────────
    print(f"\n{bold('System information')}\n")
    system_name   = ask_text("System / product name")
    operator_name = ask_text("Your name or organisation")

    timestamp = datetime.now(tz=timezone.utc)

    # ── Step 0: Applicability gate ────────────────────────────────────────────
    print()
    hr()
    print(f"\n{bold('Step 0 — Applicability Gate')}\n")
    print("  Answer the following three questions to confirm Art. 14 applies.\n")

    q1 = ask_yes_no("Is this AI system listed in Annex III of the EU AI Act?")
    q2 = ask_yes_no("Is the system deployed or used in the EU, or does it affect persons in the EU?")
    q3 = ask_yes_no("Is the system classified as high-risk under Art. 6?")

    gate_answers = {
        "q1": "Yes" if q1 else "No",
        "q2": "Yes" if q2 else "No",
        "q3": "Yes" if q3 else "No",
    }

    if not (q1 and q2 and q3):
        print()
        print(yellow("  Article 14 does not apply to your system based on these answers."))
        print("  No report will be generated.")
        print()
        sys.exit(0)

    print(f"\n  {green('All three conditions met — Article 14 applies.')}\n")

    # ── Step 1: Role ──────────────────────────────────────────────────────────
    hr()
    print(f"\n{bold('Step 1 — Your Role')}\n")
    print("  Select your role relative to this AI system:\n")
    roles = role_select()
    role_display = " / ".join(r.capitalize() for r in roles)
    print(f"\n  Role(s) selected: {green(role_display)}\n")

    # ── Step 2: Sectors ───────────────────────────────────────────────────────
    hr()
    print(f"\n{bold('Step 2 — Annex III Sectors')}\n")
    print("  Select all Annex III sectors that apply to this system:\n")
    sector_indices = multi_select(ANNEX_III_SECTORS, "Which sectors apply?")
    selected_sectors = [ANNEX_III_SECTORS[i] for i in sector_indices]
    biometric_selected = any("Biometrics" in s for s in selected_sectors)

    if selected_sectors:
        print(f"\n  Sectors selected: {green(', '.join(selected_sectors))}")
    else:
        print(f"\n  {yellow('No sectors selected.')} Section C will be skipped.")

    if biometric_selected:
        print(f"  {cyan('Sector 1 (Biometrics) selected — Section C checks will be shown.')}")
    print()

    # ── Determine which checks to run ─────────────────────────────────────────
    applicable: list[dict] = []
    for chk in CHECKS:
        sec = chk["section"]

        # Section A: provider only
        if sec == "A" and "provider" not in roles:
            continue
        # Section B: deployer only
        if sec == "B" and "deployer" not in roles:
            continue
        # Section C: biometric only
        if chk["biometric_only"] and not biometric_selected:
            continue
        # Sections D and E: always shown (provider + deployer)
        applicable.append(chk)

    # ── Walk through checks ───────────────────────────────────────────────────
    results: list[dict] = []
    total = len(applicable)

    current_section = None
    current_subsection = None

    for idx, chk in enumerate(applicable, 1):
        sec = chk["section"]
        sub = chk["subsection"]

        # Print section header
        if sec != current_section:
            current_section = sec
            current_subsection = None
            print()
            hr()
            sec_title = SECTION_TITLES.get(sec, f"Section {sec}")
            print(f"\n{bold(sec_title)}\n")

        # Print subsection header
        if sub != current_subsection:
            current_subsection = sub
            from checks import SUBSECTION_TITLES
            sub_title = SUBSECTION_TITLES.get(sub, sub)
            if sub != sec:  # avoid repeating for flat sections C/D/E
                print(f"  {cyan(sub_title)}\n")

        # Display the check
        print(f"  {bold(chk['id'])}  [{idx}/{total}]")
        print(f"  {chk['article']} — {chk['title']}")
        print()
        # Word-wrap the requirement at ~66 chars
        req_words = chk["requirement"].split()
        line = "  "
        wrapped = []
        for word in req_words:
            if len(line) + len(word) + 1 > 68:
                wrapped.append(line.rstrip())
                line = "  " + word + " "
            else:
                line += word + " "
        wrapped.append(line.rstrip())
        print("\n".join(wrapped))
        print()
        print(f"  {dim('Evidence: ' + chk['evidence'])}")
        print()

        status = ask_status(chk["id"])
        note = ""
        if status in ("partial", "gap"):
            note = ask_note()

        results.append({"check": chk, "status": status, "note": note})
        print()

    # ── Compute tally and overall status ─────────────────────────────────────
    tally = {"compliant": 0, "partial": 0, "gap": 0, "skipped": 0}
    for r in results:
        tally[r["status"]] += 1
    total_checked = sum(tally.values())

    if tally["gap"] == 0 and tally["partial"] == 0:
        overall = "Compliant"
        overall_fmt = green(bold("Compliant"))
    elif tally["gap"] == 0:
        overall = "Conditionally compliant"
        overall_fmt = yellow(bold("Conditionally compliant"))
    else:
        overall = "Non-compliant"
        overall_fmt = red(bold("Non-compliant"))

    hr("═")
    print(f"\n{bold('Assessment complete — Summary')}\n")
    print(f"  {green('✓')} Compliant : {tally['compliant']}")
    print(f"  {yellow('~')} Partial   : {tally['partial']}")
    print(f"  {red('✗')} Gap       : {tally['gap']}")
    print(f"  {dim('-')} Skipped   : {tally['skipped']}")
    print(f"  ─────────────────")
    print(f"    Total     : {total_checked}")
    print()
    print(f"  Overall status: {overall_fmt}")
    print()

    # ── Generate and write report ─────────────────────────────────────────────
    report_md = generate_report(
        system_name=system_name,
        operator_name=operator_name,
        timestamp=timestamp,
        roles=roles,
        sectors=selected_sectors,
        gate_answers=gate_answers,
        results=results,
        applicable_checks=applicable,
    )

    report_path = write_report(report_md, timestamp)

    hr("═")
    print(f"\n  {green('Report written to:')}")
    print(f"  {bold(report_path)}")
    print()


if __name__ == "__main__":
    main()
