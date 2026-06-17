#!/usr/bin/env python3
"""
Independent verifier for GDPR compliance assessment artifacts.

No dependency on the checker package — uses stdlib only.

Usage:
    python verify_assessment.py <artifact.json> --key <signing_key>
    python verify_assessment.py <artifact.json> --key-env SIGNING_KEY
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path


def _sign_payload(payload: dict, signing_key: str) -> str:
    """Compute HMAC-SHA256 hex digest over canonical JSON of payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify(artifact: dict, signing_key: str) -> bool:
    """Return True if the artifact signature is valid."""
    try:
        payload = artifact["payload"]
        stored_sig = artifact["signature"]
    except (KeyError, TypeError):
        return False

    expected = _sign_payload(payload, signing_key)
    return hmac.compare_digest(expected, stored_sig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_assessment.py",
        description=(
            "Verify the HMAC-SHA256 signature on a GDPR compliance assessment artifact. "
            "This verifier has zero runtime dependencies (stdlib only)."
        ),
    )
    parser.add_argument("artifact", help="Path to the signed JSON artifact file")

    key_group = parser.add_mutually_exclusive_group(required=True)
    key_group.add_argument("--key", help="Signing key (plain text)")
    key_group.add_argument(
        "--key-env",
        metavar="VAR",
        help="Name of the environment variable holding the signing key",
    )

    args = parser.parse_args(argv)

    # Resolve signing key
    if args.key:
        signing_key = args.key
    else:
        signing_key = os.environ.get(args.key_env, "")
        if not signing_key:
            print(
                f"ERROR: Environment variable {args.key_env!r} is not set or empty.",
                file=sys.stderr,
            )
            return 2

    # Load artifact
    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        print(f"ERROR: Artifact file not found: {artifact_path}", file=sys.stderr)
        return 2

    try:
        with open(artifact_path, "r", encoding="utf-8") as fh:
            artifact = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in artifact: {exc}", file=sys.stderr)
        return 2

    # Print metadata
    payload = artifact.get("payload", {})
    print("=" * 60)
    print("GDPR COMPLIANCE ASSESSMENT — VERIFICATION RESULT")
    print("=" * 60)
    print(f"Assessment ID : {payload.get('assessment_id', 'N/A')}")
    print(f"Organization  : {payload.get('organization_id', 'N/A')}")
    print(f"Completed At  : {payload.get('completed_at', 'N/A')}")
    print(f"Vertical      : {payload.get('vertical', 'N/A')}")
    print(f"Overall Score : {payload.get('overall_score', 'N/A')} / 100")
    print(f"Maturity Tier : {payload.get('maturity_tier', 'N/A')}")
    print(f"Critical Gaps : {len(payload.get('critical_gaps', []))}")
    print(f"Schema Version: {payload.get('schema_version', 'N/A')}")

    if "signing_key_id" in artifact:
        print(f"Signing Key ID: {artifact['signing_key_id']}")

    print()

    if verify(artifact, signing_key):
        print("RESULT: VALID")
        print("The artifact signature is authentic. The assessment has not been tampered with.")
        return 0
    else:
        print("RESULT: INVALID", file=sys.stderr)
        print(
            "WARNING: Signature mismatch. The artifact may have been tampered with "
            "or an incorrect signing key was provided.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
