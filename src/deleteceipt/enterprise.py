"""Enterprise deletion receipt schema.

Extends the core receipt with fields required for GDPR Article 30
documentation, HIPAA, and SOC 2 compliance:

  - ``data_categories``     — sorted GDPR data category strings
  - ``storage_layers``      — systems from which data was deleted
  - ``retention_exceptions`` — data NOT deleted with encoded reasons
  - ``initiated_by``        — source of the deletion request
  - ``request_reference``   — DSR ticket ID for cross-system correlation
  - ``schema_version``      — forward-compatibility version string

The signing mechanism is identical to the core HMAC-SHA256 path.

Usage::

    from deleteceipt.enterprise import issue_enterprise_receipt, verify_enterprise_receipt
    from datetime import datetime, timezone

    receipt = issue_enterprise_receipt(
        user_id="usr-123",
        request_timestamp=datetime.now(timezone.utc),
        data_categories=["contact_information", "uploaded_content"],
        storage_layers=["postgres:users", "s3:uploads:3_objects_deleted"],
        retention_exceptions=["financial_records:stripe:legal_obligation:7yr"],
        initiated_by="user_request",
        request_reference="DSR-2025-06-17-003892",
        signing_key="my-secret-key",
        signing_key_id="key/v1/2025-06-01",
    )

    ok = verify_enterprise_receipt(receipt, "my-secret-key")
    assert ok
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Literal


_INITIATED_BY = Literal["user_request", "admin", "automated_ttl", "legal_request"]


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True)


def _sign(canonical: str, key: str | bytes) -> str:
    if isinstance(key, str):
        key = key.encode()
    sig = hmac.new(key, canonical.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def issue_enterprise_receipt(
    user_id: str,
    request_timestamp: datetime,
    data_categories: list[str],
    storage_layers: list[str],
    signing_key: str | bytes,
    retention_exceptions: list[str] | None = None,
    initiated_by: str = "user_request",
    request_reference: str = "",
    signing_key_id: str | None = None,
    schema_version: str = "1.0",
) -> dict:
    """Issue a signed enterprise deletion receipt.

    Args:
        user_id: Internal platform user identifier.
        request_timestamp: When the deletion request was received.
        data_categories: Sorted list of GDPR Article 30 data category strings
            (e.g. ``["behavioral_analytics", "contact_information"]``).
        storage_layers: Sorted list of storage systems from which data was
            successfully deleted (e.g. ``["postgres:users", "redis:sessions"]``).
        signing_key: HMAC-SHA256 signing key.
        retention_exceptions: Data categories or storage layers NOT deleted,
            with the reason encoded as ``"category:system:reason:period"``
            (e.g. ``"payment_records:stripe:legal_obligation:7yr"``).
            Omitting a legitimate exception makes the receipt inaccurate.
        initiated_by: Source of the deletion request.  One of:
            ``"user_request"``, ``"admin"``, ``"automated_ttl"``,
            ``"legal_request"``.
        request_reference: External reference for cross-system correlation
            (e.g. a DSR ticket ID).
        signing_key_id: Human-readable key version identifier.  Required for
            key rotation — store historical keys indexed by this ID.
        schema_version: Receipt schema version for forward compatibility.

    Returns:
        Signed receipt dict.  Store in an append-only audit collection.
    """
    now = datetime.now(timezone.utc)

    payload: dict = {
        "receipt_id": str(uuid.uuid4()),
        "user_id": user_id,
        "request_timestamp": request_timestamp.isoformat(),
        "deletion_timestamp": now.isoformat(),
        "data_categories": sorted(data_categories),
        "storage_layers": sorted(storage_layers),
        "retention_exceptions": sorted(retention_exceptions or []),
        "initiated_by": initiated_by,
        "request_reference": request_reference,
        "schema_version": schema_version,
    }

    canonical = _canonical(payload)
    signature = _sign(canonical, signing_key)

    result: dict = {"payload": payload, "signature": signature}
    if signing_key_id is not None:
        result["signing_key_id"] = signing_key_id
    return result


def verify_enterprise_receipt(receipt: dict, signing_key: str | bytes) -> bool:
    """Verify the HMAC-SHA256 signature on an enterprise receipt.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        receipt: Receipt dict as returned by ``issue_enterprise_receipt()``.
        signing_key: The same key used to sign the receipt.

    Returns:
        ``True`` if the signature is valid and the payload has not been
        tampered with.
    """
    payload = receipt.get("payload")
    stored_sig = receipt.get("signature")
    if payload is None or stored_sig is None:
        return False

    canonical = _canonical(payload)
    expected = _sign(canonical, signing_key)
    return hmac.compare_digest(stored_sig, expected)
