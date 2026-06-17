# EU AI Act Article 14 — Human Oversight Compliance Checker

An interactive CLI tool for security operators to self-assess whether a
high-risk AI system complies with EU AI Act Article 14 (Human Oversight).

## What it does

- Walks you through an applicability gate (3 yes/no questions)
- Asks your role: provider, deployer, or both
- Asks which Annex III sectors apply (multi-select)
- Presents every relevant check from Sections A–E, one at a time
- Accepts four statuses per check: Compliant / Partial / Gap / Skip
- Captures optional notes on any gap or partial item
- Produces a filled-out Markdown report in the current directory

## How to run

```
python checker.py
```

Requires Python 3.10+. No third-party packages needed.

## Output

A file named `report_YYYY-MM-DD_HHMMSS.md` is written to the directory
where you run the command. It contains:

- System metadata and gate answers
- Per-section check tables with status and notes
- Tally and overall compliance status
- Remediation log for gaps and partial items
- Evidence checklist for items not marked compliant
- Caveats and legal disclaimer
