"""ECDSA-based deletion receipts (P-256 / secp256r1).

Unlike the HMAC path, ECDSA enables *asymmetric* verification: the server
signs with a private key that it never discloses, and any third party can
verify using only the public key.  This is a stronger trust model because
verifiers don't need to trust that the server is using the correct key — they
can check independently.

The receipt is self-contained: the public key PEM is embedded in
``signing_public_key_pem`` so that ``verify_receipt_ecdsa`` requires no
external key material.

Signing mechanism
-----------------
1. Build the same canonical JSON payload as the HMAC path (sorted keys).
2. Sign the UTF-8 encoding of that JSON with ECDSA/P-256/SHA-256.
3. Encode the raw DER signature as base64 and store in
   ``server_signature_ecdsa``.
4. Embed the public key PEM in ``signing_public_key_pem``.

This module requires the ``cryptography`` package (``pip install
deleteceipt[ecdsa]``).
"""
from __future__ import annotations

import base64
import json
from datetime import datetime

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature,
        encode_dss_signature,
    )
    from cryptography.exceptions import InvalidSignature
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "ECDSA receipt support requires the 'cryptography' package. "
        "Install it with: pip install deleteceipt[ecdsa]"
    ) from _exc


def generate_keypair() -> tuple[str, str]:
    """Generate a new P-256 (secp256r1) ECDSA keypair.

    Returns:
        A (private_key_pem, public_key_pem) tuple, both as UTF-8 strings.
        Store the private key securely; distribute/embed the public key freely.
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True).encode()


def issue_receipt_ecdsa(
    job_id: str,
    file_hash: str,
    uploaded_at: datetime,
    processing_completed_at: datetime,
    deleted_at: datetime,
    private_key_pem: str,
    files_deleted: list[dict] | None = None,
    key_version: str | None = None,
) -> dict:
    """Build and ECDSA-sign a deletion receipt.

    Args:
        job_id: Unique identifier for the processing job.
        file_hash: SHA-256 hex digest computed at upload time via
            ``compute_file_hash()``.
        uploaded_at: When the file was uploaded.
        processing_completed_at: When processing finished.
        deleted_at: When all files were deleted.
        private_key_pem: PKCS8 PEM-encoded P-256 private key (from
            ``generate_keypair()``).
        files_deleted: Optional list of dicts with keys: path, size_bytes,
            role (one of "input", "output", "intermediate").
        key_version: Optional key version identifier for key rotation support.

    Returns:
        Signed receipt dict containing ``server_signature_ecdsa`` (base64
        DER) and ``signing_public_key_pem`` for self-contained verification.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

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
    # Sign → DER bytes → base64
    der_sig = private_key.sign(canonical, ec.ECDSA(hashes.SHA256()))
    sig_b64 = base64.b64encode(der_sig).decode()

    payload["server_signature_ecdsa"] = sig_b64
    payload["signing_public_key_pem"] = public_pem
    return payload


def verify_receipt_ecdsa(receipt: dict, public_key_pem: str | None = None) -> bool:
    """Verify the ECDSA signature on a receipt.

    The receipt is self-contained: if ``public_key_pem`` is not provided, the
    key embedded in ``receipt["signing_public_key_pem"]`` is used.

    Args:
        receipt: Receipt dict as returned by ``issue_receipt_ecdsa()``.
        public_key_pem: PEM-encoded P-256 public key. If ``None``, falls back
            to the key stored inside the receipt.

    Returns:
        ``True`` if the signature is cryptographically valid and the payload
        has not been tampered with.  ``False`` otherwise.
    """
    receipt = dict(receipt)
    sig_b64 = receipt.pop("server_signature_ecdsa", None)
    embedded_pub = receipt.pop("signing_public_key_pem", None)

    if sig_b64 is None:
        return False

    pem_to_use = public_key_pem or embedded_pub
    if pem_to_use is None:
        return False

    try:
        der_sig = base64.b64decode(sig_b64)
        public_key = serialization.load_pem_public_key(pem_to_use.encode())
        canonical = _canonical(receipt)
        public_key.verify(der_sig, canonical, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, Exception):
        return False
