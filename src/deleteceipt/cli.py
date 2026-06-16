"""Command-line interface for deleteceipt.

Subcommands
-----------
deleteceipt verify <receipt.json> --key <hmac-key>
    Verify an HMAC-SHA256-signed receipt.

deleteceipt verify-ecdsa <receipt.json>
    Verify an ECDSA-signed receipt using the embedded public key.

deleteceipt keygen
    Generate a fresh P-256 ECDSA keypair and print PEMs to stdout.

deleteceipt inspect <receipt.json>
    Pretty-print all fields in a human-readable table (no verification).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_receipt(path: str) -> dict:
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def _col_widths(rows: list[tuple[str, str]]) -> tuple[int, int]:
    w1 = max(len(r[0]) for r in rows)
    w2 = max(len(r[1]) for r in rows)
    return w1, w2


def _print_table(rows: list[tuple[str, str]]) -> None:
    if not rows:
        return
    w1, w2 = _col_widths(rows)
    sep = "+" + "-" * (w1 + 2) + "+" + "-" * (w2 + 2) + "+"
    print(sep)
    for key, val in rows:
        print(f"| {key:<{w1}} | {val:<{w2}} |")
        print(sep)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_verify(args: argparse.Namespace) -> int:
    from deleteceipt.receipt import verify_receipt

    receipt = _load_receipt(args.receipt)
    ok = verify_receipt(receipt, args.key)
    if ok:
        print("OK  — HMAC-SHA256 signature is valid.")
        return 0
    else:
        print("INVALID — signature verification failed.", file=sys.stderr)
        print(
            "  Possible causes: wrong key, tampered payload, or receipt was not "
            "issued by this server.",
            file=sys.stderr,
        )
        return 1


def cmd_verify_ecdsa(args: argparse.Namespace) -> int:
    try:
        from deleteceipt.ecdsa_receipt import verify_receipt_ecdsa
    except ImportError:
        print(
            "Error: ECDSA support is not installed. "
            "Run: pip install deleteceipt[ecdsa]",
            file=sys.stderr,
        )
        return 2

    receipt = _load_receipt(args.receipt)

    pub_key_pem: str | None = None
    if args.key:
        try:
            pub_key_pem = Path(args.key).read_text()
        except FileNotFoundError:
            print(f"Error: public key file not found: {args.key}", file=sys.stderr)
            return 1

    ok = verify_receipt_ecdsa(receipt, public_key_pem=pub_key_pem)
    if ok:
        print("OK  — ECDSA (P-256) signature is valid.")
        return 0
    else:
        print("INVALID — ECDSA signature verification failed.", file=sys.stderr)
        print(
            "  Possible causes: tampered payload, wrong public key, or the receipt "
            "was not issued by the claimed server.",
            file=sys.stderr,
        )
        return 1


def cmd_keygen(args: argparse.Namespace) -> int:
    try:
        from deleteceipt.ecdsa_receipt import generate_keypair
    except ImportError:
        print(
            "Error: ECDSA support is not installed. "
            "Run: pip install deleteceipt[ecdsa]",
            file=sys.stderr,
        )
        return 2

    private_pem, public_pem = generate_keypair()
    print("# PRIVATE KEY — keep secret, never distribute")
    print(private_pem)
    print("# PUBLIC KEY — embed in receipts / distribute to verifiers")
    print(public_pem)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    receipt = _load_receipt(args.receipt)

    # Build ordered rows: known fields first, then extras
    KNOWN_ORDER = [
        "job_id",
        "file_hash_sha256",
        "uploaded_at",
        "processing_completed_at",
        "deleted_at",
        "key_version",
        "files_deleted",
        "signing_public_key_pem",
        "server_signature",
        "server_signature_ecdsa",
    ]

    rows: list[tuple[str, str]] = []
    seen: set[str] = set()

    for key in KNOWN_ORDER:
        if key in receipt:
            val = receipt[key]
            if isinstance(val, (dict, list)):
                val_str = json.dumps(val, ensure_ascii=False)
                # Truncate very long values
                if len(val_str) > 120:
                    val_str = val_str[:117] + "..."
            elif isinstance(val, str) and len(val) > 120:
                val_str = val[:117] + "..."
            else:
                val_str = str(val)
            rows.append((key, val_str))
            seen.add(key)

    for key, val in receipt.items():
        if key not in seen:
            val_str = str(val)
            if len(val_str) > 120:
                val_str = val_str[:117] + "..."
            rows.append((key, val_str))

    _print_table(rows)
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deleteceipt",
        description="Inspect and verify cryptographic deletion receipts.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # verify
    p_verify = sub.add_parser(
        "verify",
        help="Verify an HMAC-SHA256-signed receipt.",
    )
    p_verify.add_argument("receipt", metavar="receipt.json", help="Path to receipt JSON file.")
    p_verify.add_argument(
        "--key",
        required=True,
        metavar="KEY",
        help="HMAC-SHA256 signing key (plain text).",
    )

    # verify-ecdsa
    p_vecdsa = sub.add_parser(
        "verify-ecdsa",
        help="Verify an ECDSA-signed receipt (uses embedded public key by default).",
    )
    p_vecdsa.add_argument("receipt", metavar="receipt.json", help="Path to receipt JSON file.")
    p_vecdsa.add_argument(
        "--key",
        required=False,
        default=None,
        metavar="PUBLIC_KEY_PEM",
        help=(
            "Path to a PEM public key file.  If omitted, the public key embedded "
            "inside the receipt is used."
        ),
    )

    # keygen
    sub.add_parser(
        "keygen",
        help="Generate a new P-256 ECDSA keypair (prints PEMs to stdout).",
    )

    # inspect
    p_inspect = sub.add_parser(
        "inspect",
        help="Pretty-print all receipt fields without verifying.",
    )
    p_inspect.add_argument("receipt", metavar="receipt.json", help="Path to receipt JSON file.")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "verify": cmd_verify,
        "verify-ecdsa": cmd_verify_ecdsa,
        "keygen": cmd_keygen,
        "inspect": cmd_inspect,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = handler(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
