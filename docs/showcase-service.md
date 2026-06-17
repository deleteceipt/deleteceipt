# Showcase Public Service: A Verifiable GDPR Erasure Processor

## Concept

A free public web service where anyone can submit an Article 17 "right to be forgotten" request against their own data on a demo platform and receive a cryptographically signed deletion receipt they can actually keep — and verify independently, forever, even after the service shuts down.

This is the demonstration no other privacy tool makes: not a promise, not a policy, not a screenshot. A signed artifact.

**Name candidates:** `forgetme.io` · `erasure.dev` · `deleteme.io`

---

## The User Journey

1. **Upload** a file (tax document, medical form, contract, anything)
2. **Processing** runs — OCR, text extraction, structured output — simulating a real document processing platform
3. **Download** the result
4. **Request deletion** — manually via button, or wait for the automatic 1-hour TTL
5. **Receive a signed deletion receipt** — JSON + plain-English card + downloadable PDF
6. **Verify** the receipt independently using the open source CLI, with no trust in the platform required

Every step is instrumented. Every event is hash-chained. The transparency page shows every storage layer and its documented TTL policy in real time.

---

## How Every Open Source Candidate Is Exercised

| Component | Role in the service |
|---|---|
| `secure-tmpfs` | All processing writes go to a RAM-backed tmpfs mount — no file ever touches disk |
| `deleteceipt-audit` | Every lifecycle event (upload → process → delete) is appended to a hash-chained audit log in real time |
| `deletion-scheduler` | 1-hour TTL auto-deletes files if the user does not request deletion manually; configurable per compliance regime |
| `legal-hold-gate` | A "demo legal hold" toggle shows what happens when deletion is blocked — issues a hold notification instead of a receipt |
| `crypto-shredder` | Backup snapshots and log aggregators use per-user KMS keys; key deletion = cryptographic erasure of all residual copies |
| `deleteceipt` (core) | Issues HMAC-SHA256 signed receipt on deletion; ECDSA/P-256 variant available |
| `deleteceipt-enterprise` | Receipt includes `data_categories`, `storage_layers` with counts, `retention_exceptions` with reasons, `initiated_by`, `request_reference` |
| `receipt-renderer` | Renders plain-English summary card and downloadable PDF alongside the raw canonical JSON |
| `deleteceipt-verify` | "Verify this receipt" button — and a CLI the user can run locally forever with no platform dependency |
| `deleteceipt-reconcile` | Nightly reconciliation job; dashboard shows any inconsistencies found, remediation taken, and supplementary receipts issued |
| `deletion-audit-test` | CI badge on the homepage; integration test suite runs against live infrastructure on every deploy |
| `deletion-inventory` | Public transparency page listing every storage layer, its retention policy, and its deletion mechanism |

---

## Why This Is the Right Showcase

### For non-technical users
Compliance officers, regulators, legal teams, and journalists receive something they can hold: a receipt. It is specific (this file, this hash, this timestamp), contemporaneous (generated at the moment of deletion), verifiable (the hash and signature can be checked), and portable (it lives on their machine, not the platform's).

### For engineers
A live, inspectable reference architecture. Every component is open source. The transparency page documents every storage layer. The CI pipeline is public. The deletion pipeline can be audited by reading the code.

### For regulators
The receipt maps directly onto GDPR Article 17 evidentiary requirements — `data_categories` corresponds to Article 30 Records of Processing Activities categories; `storage_layers` documents the specific systems from which data was erased; `retention_exceptions` honestly records what was not deleted and why. The audit log provides the defense-in-depth record regulators look for beyond the receipt itself.

---

## Architecture

```
User Browser
    │
    ▼
API Gateway (Flask / FastAPI)
    │
    ├── Upload → secure-tmpfs mount (/mnt/secure-tmp/{job_id}/)
    │
    ├── Processing Worker (Celery)
    │       └── Reads/writes only to tmpfs
    │
    ├── deletion-scheduler (Celery Beat, every 5 min)
    │       └── Queries audit log for expired jobs
    │
    ├── Deletion Pipeline
    │       ├── legal-hold-gate (check holds table)
    │       ├── delete tmpfs files (delete_directory_tree)
    │       ├── crypto-shredder (delete KMS key for user)
    │       ├── deleteceipt-audit (append 'deleted' event)
    │       ├── deleteceipt-enterprise (issue signed receipt)
    │       └── receipt-renderer (generate HTML card + PDF)
    │
    ├── deleteceipt-reconcile (nightly)
    │
    └── deletion-inventory (transparency page, live query)

Storage Layers (all documented on transparency page)
    ├── tmpfs — /mnt/secure-tmp — TTL: 1 hour, mechanism: os.remove()
    ├── MongoDB — jobs, audit_log, receipts — TTL: per-collection policy
    ├── Redis — session cache — TTL: 1 hour, mechanism: explicit invalidation
    └── KMS — per-user keys — TTL: deleted on job deletion
```

---

## The Transparency Page

A live public page showing every storage layer the service operates, its documented retention policy, its deletion mechanism, and the last time the deletion-inventory scan confirmed it was clean. This is itself a reference implementation that organizations can copy for their own GDPR Article 30 records.

Example entries:

| Storage Layer | Data Held | Retention Policy | Deletion Mechanism | Last Verified |
|---|---|---|---|---|
| `tmpfs:/mnt/secure-tmp` | Raw uploaded files, processing intermediates | 1 hour from upload | `os.remove()` + directory rmdir | Live |
| `mongodb:jobs` | Job metadata, status | 30 days after deletion | Hard delete on TTL expiry | 2025-06-17 |
| `mongodb:audit_log` | Deletion receipts, audit entries | 7 years (compliance) | Retained — this is the evidence record | N/A |
| `redis:session_cache` | Session tokens | 1 hour | Explicit `DEL` on deletion pipeline | Live |
| `aws-kms:user-keys` | Per-user encryption keys | Deleted with job | KMS `ScheduleKeyDeletion` | Live |

---

## The Receipt the User Keeps

```json
{
  "payload": {
    "receipt_id": "f3a7c1e2-9b4d-4f8a-b2e1-7c3d5a9f0e6b",
    "user_id": "usr_4829abc7-de31-4f2a-9c18-3b7e5f1a2d04",
    "request_timestamp": "2025-06-17T09:23:17.441882+00:00",
    "deletion_timestamp": "2025-06-17T09:23:19.882341+00:00",
    "data_categories": ["uploaded_content", "usage_logs"],
    "storage_layers": [
      "tmpfs:processing-files:1_file_deleted",
      "mongodb:jobs",
      "redis:session_cache"
    ],
    "retention_exceptions": [],
    "initiated_by": "user_request",
    "request_reference": "DSR-2025-06-17-003892",
    "schema_version": "1.0"
  },
  "signature": "7mK3nP9qR2sT5uV8wXlyZ4aB6cD0eF2gH4iJ7kL9mN1oP3qR5sT8uVOwX2yZ5=",
  "signing_key_id": "deletion-signing-key/v3/2025-06-01"
}
```

This receipt is valid and verifiable forever. When the service eventually shuts down, the user runs:

```bash
python verify_receipt.py receipt.json <signing_key>
# VALID: Receipt f3a7c1e2 verified successfully.
#   User:      usr_4829abc7
#   Deleted:   2025-06-17T09:23:19
#   Layers:    3 storage layer(s)
```

No trust in the platform required. No account needed. No API call. The receipt stands alone.

---

## Positioning

> **"The world's first verifiable deletion demo."**

Every other privacy tool makes a promise. This one hands you evidence.

The service is positioned not as a production document processor but as a reference implementation and educational tool — the living companion to the book and the `deleteceipt` library. Organizations evaluating deletion receipt architecture can inspect every layer of the stack, run the verification CLI against receipts they generate themselves, and copy the transparency page format for their own Article 30 documentation.
