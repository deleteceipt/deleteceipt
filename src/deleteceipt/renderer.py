"""Plain-language receipt renderer.

Translates a raw deletion receipt (core or enterprise) into human-readable
formats suitable for non-technical users — compliance officers, healthcare
administrators, legal teams — without altering the underlying canonical JSON.

Outputs:
  - ``text``  — plain-text summary
  - ``html``  — self-contained HTML card for embedding in a UI
  - ``json``  — the original receipt (pass-through, for API responses)

The plain-language layer translates the receipt; it does not replace it.
The canonical JSON record is always included alongside any rendered output.

Usage::

    from deleteceipt.renderer import render_receipt

    # Core receipt
    summary = render_receipt(receipt, fmt="text")
    html_card = render_receipt(receipt, fmt="html")

    # Enterprise receipt
    summary = render_receipt(enterprise_receipt, fmt="text", is_enterprise=True)
"""
from __future__ import annotations

import json
from datetime import datetime


def _fmt_ts(iso: str) -> str:
    """Format an ISO 8601 timestamp as a readable string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        return iso


def _render_text_core(receipt: dict) -> str:
    job_id = receipt.get("job_id", "unknown")
    file_hash = receipt.get("file_hash_sha256", "")
    uploaded = _fmt_ts(receipt.get("uploaded_at", ""))
    deleted = _fmt_ts(receipt.get("deleted_at", ""))
    files = receipt.get("files_deleted", [])
    sig = receipt.get("server_signature", receipt.get("server_signature_ecdsa", ""))
    notes = receipt.get("notes", "")

    lines = [
        "DELETION RECEIPT",
        "=" * 60,
        f"Job ID:         {job_id}",
        f"File uploaded:  {uploaded}",
        f"File deleted:   {deleted}",
        f"Files removed:  {len(files)} file(s)",
    ]
    for f in files:
        lines.append(f"  - {f.get('path', '')} ({f.get('size_bytes', 0)} bytes, role: {f.get('role', '')})")
    lines += [
        "",
        f"File fingerprint (SHA-256):",
        f"  {file_hash}",
        "",
        "Server signature (tamper-evident):",
        f"  {sig[:40]}..." if len(sig) > 40 else f"  {sig}",
    ]
    if notes:
        lines += ["", f"Note: {notes}"]
    lines += [
        "",
        "To verify this receipt, run:",
        "  deleteceipt verify receipt.json --key <your-signing-key>",
        "",
        "You can confirm this receipt refers to your specific document by",
        "computing the SHA-256 hash of your original file and comparing it",
        "to the file fingerprint above.",
    ]
    return "\n".join(lines)


def _render_text_enterprise(receipt: dict) -> str:
    payload = receipt.get("payload", receipt)
    receipt_id = payload.get("receipt_id", "unknown")
    user_id = payload.get("user_id", "unknown")
    requested = _fmt_ts(payload.get("request_timestamp", ""))
    deleted = _fmt_ts(payload.get("deletion_timestamp", ""))
    categories = payload.get("data_categories", [])
    layers = payload.get("storage_layers", [])
    exceptions = payload.get("retention_exceptions", [])
    initiated = payload.get("initiated_by", "")
    reference = payload.get("request_reference", "")
    sig = receipt.get("signature", "")

    lines = [
        "DELETION RECEIPT",
        "=" * 60,
        f"Receipt ID:       {receipt_id}",
        f"User ID:          {user_id}",
        f"Request received: {requested}",
        f"Deletion completed: {deleted}",
        f"Initiated by:     {initiated}",
    ]
    if reference:
        lines.append(f"Request reference: {reference}")
    lines += [
        "",
        "Data categories deleted:",
    ]
    for cat in categories:
        lines.append(f"  - {cat}")
    lines += [
        "",
        "Storage layers cleared:",
    ]
    for layer in layers:
        lines.append(f"  - {layer}")
    if exceptions:
        lines += [
            "",
            "Retention exceptions (data NOT deleted):",
        ]
        for exc in exceptions:
            lines.append(f"  - {exc}")
    lines += [
        "",
        "Server signature (tamper-evident):",
        f"  {sig[:40]}..." if len(sig) > 40 else f"  {sig}",
        "",
        "This receipt is cryptographically signed. Any modification to its",
        "contents will invalidate the signature. Retain this document for",
        "compliance purposes.",
    ]
    return "\n".join(lines)


def _render_html_core(receipt: dict) -> str:
    job_id = receipt.get("job_id", "unknown")
    file_hash = receipt.get("file_hash_sha256", "")
    uploaded = _fmt_ts(receipt.get("uploaded_at", ""))
    deleted = _fmt_ts(receipt.get("deleted_at", ""))
    files = receipt.get("files_deleted", [])
    sig = receipt.get("server_signature", receipt.get("server_signature_ecdsa", ""))
    notes = receipt.get("notes", "")

    files_html = "".join(
        f"<li><code>{f.get('path','')}</code> — {f.get('size_bytes',0)} bytes ({f.get('role','')})</li>"
        for f in files
    )
    note_html = f"<p class='note'><strong>Note:</strong> {notes}</p>" if notes else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Deletion Receipt — {job_id}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; color: #1a1a1a; }}
  .card {{ border: 1px solid #d0d0d0; border-radius: 8px; padding: 1.5rem; background: #fafafa; }}
  h2 {{ margin-top: 0; color: #2d6a4f; }}
  .field {{ margin: 0.5rem 0; }}
  .label {{ font-weight: 600; display: inline-block; width: 180px; }}
  .hash {{ font-family: monospace; font-size: 0.8em; word-break: break-all; background: #f0f0f0; padding: 0.25rem 0.5rem; border-radius: 4px; }}
  .note {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 0.5rem 1rem; }}
  ul {{ margin: 0.25rem 0; padding-left: 1.5rem; }}
</style>
</head>
<body>
<div class="card">
  <h2>Deletion Receipt</h2>
  <div class="field"><span class="label">Job ID:</span> {job_id}</div>
  <div class="field"><span class="label">Uploaded:</span> {uploaded}</div>
  <div class="field"><span class="label">Deleted:</span> {deleted}</div>
  <div class="field"><span class="label">Files removed:</span> {len(files)}</div>
  <ul>{files_html}</ul>
  <div class="field"><span class="label">File fingerprint:</span><br>
    <span class="hash">{file_hash}</span>
  </div>
  <div class="field"><span class="label">Signature:</span><br>
    <span class="hash">{sig}</span>
  </div>
  {note_html}
  <p style="font-size:0.85em;color:#555;">
    This receipt is cryptographically signed. You can verify it at any time
    using the open source <code>deleteceipt verify</code> CLI.
  </p>
</div>
</body>
</html>"""


def _render_html_enterprise(receipt: dict) -> str:
    payload = receipt.get("payload", receipt)
    receipt_id = payload.get("receipt_id", "unknown")
    user_id = payload.get("user_id", "unknown")
    requested = _fmt_ts(payload.get("request_timestamp", ""))
    deleted = _fmt_ts(payload.get("deletion_timestamp", ""))
    categories = payload.get("data_categories", [])
    layers = payload.get("storage_layers", [])
    exceptions = payload.get("retention_exceptions", [])
    initiated = payload.get("initiated_by", "")
    reference = payload.get("request_reference", "")
    sig = receipt.get("signature", "")

    cats_html = "".join(f"<li>{c}</li>" for c in categories)
    layers_html = "".join(f"<li><code>{l}</code></li>" for l in layers)
    exc_html = (
        "<div class='field'><span class='label'>Retention exceptions:</span><ul>"
        + "".join(f"<li>{e}</li>" for e in exceptions)
        + "</ul></div>"
    ) if exceptions else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Deletion Receipt — {receipt_id}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; color: #1a1a1a; }}
  .card {{ border: 1px solid #d0d0d0; border-radius: 8px; padding: 1.5rem; background: #fafafa; }}
  h2 {{ margin-top: 0; color: #2d6a4f; }}
  .field {{ margin: 0.5rem 0; }}
  .label {{ font-weight: 600; display: inline-block; width: 200px; }}
  .hash {{ font-family: monospace; font-size: 0.8em; word-break: break-all; background: #f0f0f0; padding: 0.25rem 0.5rem; border-radius: 4px; }}
  ul {{ margin: 0.25rem 0; padding-left: 1.5rem; }}
</style>
</head>
<body>
<div class="card">
  <h2>Deletion Receipt</h2>
  <div class="field"><span class="label">Receipt ID:</span> {receipt_id}</div>
  <div class="field"><span class="label">User ID:</span> {user_id}</div>
  <div class="field"><span class="label">Request received:</span> {requested}</div>
  <div class="field"><span class="label">Deletion completed:</span> {deleted}</div>
  <div class="field"><span class="label">Initiated by:</span> {initiated}</div>
  <div class="field"><span class="label">Reference:</span> {reference}</div>
  <div class="field"><span class="label">Data categories:</span><ul>{cats_html}</ul></div>
  <div class="field"><span class="label">Storage layers:</span><ul>{layers_html}</ul></div>
  {exc_html}
  <div class="field"><span class="label">Signature:</span><br>
    <span class="hash">{sig}</span>
  </div>
  <p style="font-size:0.85em;color:#555;">
    This receipt is cryptographically signed and suitable for inclusion in
    GDPR erasure response documentation, HIPAA audit files, or vendor
    management records.
  </p>
</div>
</body>
</html>"""


def render_receipt(
    receipt: dict,
    fmt: str = "text",
    is_enterprise: bool = False,
) -> str:
    """Render a deletion receipt in the requested format.

    Args:
        receipt: Core receipt dict (from ``issue_receipt``) or enterprise
                 receipt dict (from ``issue_enterprise_receipt``).
        fmt: Output format — ``"text"``, ``"html"``, or ``"json"``.
        is_enterprise: Set ``True`` for enterprise receipts; auto-detected
                       if the receipt contains a ``"payload"`` key.

    Returns:
        Rendered string in the requested format.
    """
    # Auto-detect enterprise format
    if "payload" in receipt:
        is_enterprise = True

    if fmt == "json":
        return json.dumps(receipt, indent=2)

    if fmt == "html":
        return _render_html_enterprise(receipt) if is_enterprise else _render_html_core(receipt)

    # Default: text
    return _render_text_enterprise(receipt) if is_enterprise else _render_text_core(receipt)
