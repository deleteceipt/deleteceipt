"""deleteceipt — cryptographic proof-of-deletion receipts.

Core API (no external dependencies):
    compute_file_hash(data)         -> str  (SHA-256 hex digest, call at upload time)
    issue_receipt(...)              -> dict (HMAC-SHA256 signed deletion receipt)
    verify_receipt(receipt, key)    -> bool (verify HMAC signature)

ECDSA API (requires ``pip install deleteceipt[ecdsa]``):
    generate_keypair()              -> (private_key_pem, public_key_pem)
    issue_receipt_ecdsa(...)        -> dict (ECDSA-signed deletion receipt)
    verify_receipt_ecdsa(receipt)   -> bool (self-contained ECDSA verification)

Audit log API:
    AuditLog                        — synchronous, hash-chained audit log
    AsyncAuditLog                   — asyncio-compatible counterpart
"""
from .receipt import compute_file_hash, issue_receipt, verify_receipt
from .audit import AuditLog, AsyncAuditLog
from .ecdsa_receipt import generate_keypair, issue_receipt_ecdsa, verify_receipt_ecdsa

__all__ = [
    # HMAC core
    "compute_file_hash",
    "issue_receipt",
    "verify_receipt",
    # ECDSA
    "generate_keypair",
    "issue_receipt_ecdsa",
    "verify_receipt_ecdsa",
    # Audit log
    "AuditLog",
    "AsyncAuditLog",
]
