"""
CLI entry point for the GDPR Compliance Checker.

Usage:
    python -m checker.cli verify <artifact.json> [--key KEY] [--key-env VAR]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .report import verify_artifact


def _cmd_verify(args: argparse.Namespace) -> int:
    """Verify a signed assessment artifact."""
    path = Path(args.artifact)
    if not path.exists():
        print(f"ERROR: Artifact file not found: {path}", file=sys.stderr)
        return 2

    try:
        with open(path, "r", encoding="utf-8") as fh:
            artifact = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in artifact: {exc}", file=sys.stderr)
        return 2

    # Resolve signing key
    if args.key:
        signing_key = args.key
    elif args.key_env:
        signing_key = os.environ.get(args.key_env, "")
        if not signing_key:
            print(
                f"ERROR: Environment variable {args.key_env!r} is not set or empty.",
                file=sys.stderr,
            )
            return 2
    else:
        print(
            "ERROR: Provide --key <signing_key> or --key-env <ENV_VAR>.",
            file=sys.stderr,
        )
        return 2

    payload = artifact.get("payload", {})
    print(f"Assessment ID : {payload.get('assessment_id', 'N/A')}")
    print(f"Organization  : {payload.get('organization_id', 'N/A')}")
    print(f"Completed At  : {payload.get('completed_at', 'N/A')}")
    print(f"Vertical      : {payload.get('vertical', 'N/A')}")
    print(f"Overall Score : {payload.get('overall_score', 'N/A')} / 100")
    print(f"Maturity Tier : {payload.get('maturity_tier', 'N/A')}")
    print()

    if verify_artifact(artifact, signing_key):
        print("SIGNATURE: VALID")
        return 0
    else:
        print("SIGNATURE: INVALID — artifact may have been tampered with.", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m checker.cli",
        description="GDPR Compliance Checker CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # verify sub-command
    verify_p = sub.add_parser("verify", help="Verify a signed assessment artifact")
    verify_p.add_argument("artifact", help="Path to the JSON artifact file")
    key_group = verify_p.add_mutually_exclusive_group(required=True)
    key_group.add_argument("--key", help="Signing key (plain text)")
    key_group.add_argument(
        "--key-env", metavar="VAR", help="Name of env var holding the signing key"
    )

    args = parser.parse_args(argv)

    if args.command == "verify":
        return _cmd_verify(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
