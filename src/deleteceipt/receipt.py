"""Cryptographic deletion receipts.

The signing scheme implements the mechanism described in USPTO provisional
application 64/019,899 (filed 2026-03-28):

  1. SHA-256 hash of the file is computed AT UPLOAD TIME — before deletion —
     creating a cryptographic content commitment.
  2. At deletion time a receipt payload is constructed and serialized as
     canonical JSON (keys sorted lexicographically).
  3. HMAC-SHA256 is computed over the canonical payload with a server-held key.
  4. The signed receipt is stored in an append-only datastore.

The pre-deletion timing is the critical non-obvious property: a hash computed
after deletion could be fabricated; a hash committed before deletion cannot.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime


def compute_file_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of raw file bytes.

    Call this AT UPLOAD TIME, before any deletion occurs.
    """
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True)


def _sign(canonical: str, key: str | bytes) -> str:
    if isinstance(key, str):
        key = key.encode()
    sig = hmac.new(key, canonical.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def issue_receipt(
    job_id: str,
    file_hash: str,
    uploaded_at: datetime,
    processing_completed_at: datetime,
    deleted_at: datetime,
    signing_key: str | bytes,
    files_deleted: list[dict] | None = None,
    key_version: str | None = None,
) -> dict:
    """Build and sign a deletion receipt.

    Args:
        job_id: Unique identifier for the processing job.
        file_hash: SHA-256 hex digest computed at upload time via compute_file_hash().
        uploaded_at: When the file was uploaded.
        processing_completed_at: When processing finished.
        deleted_at: When all files were deleted.
        signing_key: HMAC-SHA256 signing key (server-held, never shared).
        files_deleted: List of dicts with keys: path, size_bytes, role
                       (role is one of: "input", "output", "intermediate").
        key_version: Optional key version identifier for key rotation support.

    Returns:
        Signed receipt dict. Store this in an append-only datastore.
    """
    payload: dict = {
        "job_id": job_id,
        "file_hash_sha256": file_hash,
        "uploaded_at": uploaded_at.isoformat(),
        "processing_completed_at": processing_completed_at.isoformat(),
        "deleted_at": deleted_at.isoformat(),
        "files_deleted": files_deleted or [],
    }
    if key_version is not None:
        payload["key_version"] = key_version

    canonical = _canonical(payload)
    payload["server_signature"] = _sign(canonical, signing_key)
    return payload


def verify_receipt(receipt: dict, signing_key: str | bytes) -> bool:
    """Verify the HMAC-SHA256 signature on a receipt.

    Args:
        receipt: Receipt dict as returned by issue_receipt().
        signing_key: The same key used to sign the receipt.

    Returns:
        True if the signature is valid and the payload has not been tampered with.
    """
    receipt = dict(receipt)
    stored_sig = receipt.pop("server_signature", None)
    if stored_sig is None:
        return False
    canonical = _canonical(receipt)
    expected = _sign(canonical, signing_key)
    return hmac.compare_digest(stored_sig, expected)
