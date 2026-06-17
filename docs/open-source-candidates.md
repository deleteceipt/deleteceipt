# Open Source Candidates from "The Right to Be Forgotten"

These are distinct, buildable tools described in the book that don't yet exist as standalone open source libraries. The core `deleteceipt` receipt issuance is already published as v0.1.0 on PyPI. The items below represent the remaining open surface area.

---

## 1. `deleteceipt-audit` — Hash-Chained Audit Log Library

**What:** Append-only, hash-chained audit log with MongoDB backend. Each entry carries `seq`, `prev_hash`, and `entry_hash` computed over canonical JSON. Genesis hash = SHA-256 of empty bytes (`e3b0c44...`).

**API surface:** `create_audit_entry()`, `verify_audit_chain()`, `get_next_sequence_number()` (atomic MongoDB counter via `$inc + upsert`)

**From:** Chapters 10–11

**Why open source:** Reusable for any system that needs a tamper-evident event log, not just deletion receipts. The hash chain makes tampering detectable in principle — an auditor can verify that no entry was modified or removed after the fact.

---

## 2. `deleteceipt-verify` — Standalone Receipt Verification CLI

**What:** CLI tool (Python + Node.js) that takes a receipt JSON file and a signing key, recomputes the HMAC-SHA256 over canonical JSON, and exits 0 (valid) or 1 (tampered/invalid). Both language implementations must produce identical signatures — requires recursive key sorting at all nesting levels.

**From:** Appendix C, Chapter 12

**Why open source:** Lets receipt holders verify cryptographic integrity without trusting the issuing platform. A user can hash their original file locally and confirm it matches `file_hash_sha256` in the receipt, then verify the signature — closing the full verification loop independently.

---

## 3. `deleteceipt-reconcile` — Reconciliation Job Framework

**What:** Nightly job detecting two classes of inconsistency:
- `deleted` audit event exists but no receipt document → regenerate receipt from audit log data
- Filesystem still contains job directory despite `deleted` event → re-run filesystem deletion

Produces supplementary receipts with `supersedes` and `supplementary_run` fields. The original receipt is never deleted or modified — the supplementary receipt extends the record.

**From:** Chapters 11.3, 11.5

**Why open source:** Every deletion system needs this; it is currently reimplemented ad hoc per project. The reconciliation job is the pragmatic acknowledgment that deletion is not perfectly atomic.

---

## 4. `secure-tmpfs` — Context Manager for RAM-Backed Temporary Files

**What:** Python context manager `secure_temp_file(suffix, prefix)` that creates temp files on a configured tmpfs mount and guarantees deletion on exit even if an exception is raised. Includes ready-to-use Docker Compose and Kubernetes pod spec snippets for declaring tmpfs/emptyDir volumes.

**From:** Chapter 15.2

**Why open source:** Standard filesystem deletion (`os.remove()`) does not overwrite data on SSDs due to wear-leveling. Files written to tmpfs reside entirely in RAM — when deleted, the data is immediately released with no residual trace on physical media. A single well-tested primitive that document processing pipelines, medical imaging services, and any sensitive-file workflow can drop in.

---

## 5. `deletion-audit-test` — Integration Test Suite for Deletion Pipelines

**What:** pytest fixtures and async test patterns for verifying deletion across real infrastructure (Postgres, Elasticsearch, Redis, S3) — not mocks. Standard tests:
- Data removed from each storage layer
- Receipt issued and verifiable immediately after deletion
- Tampered receipt fails signature check
- Stored receipt retrieves from audit log and verifies
- Idempotent re-run produces no duplicate receipt

Also includes a shell-level `verify_deletion.sh` spot-check script that queries storage layers directly, bypassing application code.

**From:** Chapter 15.5

**Why open source:** The book states directly: "a deletion pipeline that has never been tested probably does not work." Deletion is not on the happy path — it is implemented under deadline pressure and tested manually once. This is the missing standard test harness.

---

## 6. `deletion-inventory` — Data Flow Audit Checklist + Scanner

**What:** CLI or library that walks a system's storage layers and produces a deletion-readiness report: which layers have documented TTL policies, which have deletion hooks wired, which are unaddressed. Covers:

- Primary database (hard delete vs. soft delete + hard-delete pipeline)
- Search indexes (Elasticsearch, OpenSearch, Solr)
- Caches (Redis, Memcached)
- Message queues and event streams (Kafka, SQS, Kinesis)
- Backup and archive storage
- Logs and observability data
- Third-party processors (CRM, analytics, error tracking)
- Machine learning models trained on user data

**From:** Chapter 15.1

**Why open source:** The book's checklist is the most comprehensive deletion audit framework published. A machine-readable, runnable version of it is a standalone compliance tool.

---

## 7. `deleteceipt-enterprise` — Enterprise Receipt Schema + Bulk Export

**What:** Extended `DeletionReceiptPayload` with fields required for organizational compliance:

| Field | Description |
|---|---|
| `data_categories` | Sorted GDPR Article 30 category strings |
| `storage_layers` | Enumerated systems with deletion counts |
| `retention_exceptions` | `category:system:reason:period` for data NOT deleted |
| `initiated_by` | `user_request` / `admin` / `automated_ttl` / `legal_request` |
| `request_reference` | DSR ticket ID for cross-system correlation |
| `schema_version` | Forward-compatibility version string |

Plus a bulk receipt export endpoint returning all receipts for an organization within a date range as individual JSON files or a consolidated archive.

**From:** Chapters 13, 15.3, Appendix B

**Why open source:** The GDPR/HIPAA/SOC 2 compliance use case requires this richer schema. The `retention_exceptions` field is especially important — omitting a legitimate retention exception does not make it disappear; it makes the receipt inaccurate and potentially misleading to regulators.

---

## 8. `receipt-anchor` — Blockchain Timestamping Adapter

**What:** Library that anchors a receipt hash (not the receipt itself) to a public or consortium blockchain, providing an independently verifiable timestamp and existence proof. Stores only `SHA-256(receipt)` on-chain; the full receipt remains off-chain. Handles transaction failure, gas estimation, confirmation waiting, and writes the on-chain tx hash back to the audit record.

**From:** Chapter 14.5

**Why open source:** The book analyzes blockchain anchoring as a meaningful but optional enhancement for high-stakes contexts where the platform's own timestamp is insufficient. Useful for healthcare, financial services, and legal contexts where a third-party timestamp strengthens the evidentiary record. An adapter, not a hard dependency.

---

## 9. `legal-hold-gate` — Legal Hold Middleware for Deletion Pipelines

**What:** Middleware/decorator that intercepts a deletion request, checks a configurable hold store (e.g., a `legal_holds` table keyed by user_id or data category), and:
- If held: blocks deletion, issues a hold notification document recording the hold's existence, the file identifier, and the reason deletion cannot proceed
- If not held: passes through to the normal deletion pipeline

When a hold is lifted, re-queues deletion and issues a receipt with hold-period metadata annotated.

**From:** Chapter 14.3

**Why open source:** The conflict between GDPR Article 17 erasure and litigation/investigation legal hold is one of the most commonly mishandled problems in data governance. GDPR Article 17(3)(e) exempts data necessary for legal claims — but the practical implementation requires careful procedural design. A reusable gate prevents ad-hoc, error-prone reimplementation.

---

## 10. `crypto-shredder` — Per-User Encryption Key Deletion Utility

**What:** Library implementing cryptographic erasure: encrypts user data with a per-user KMS-managed key; deletion = deleting the key, making ciphertext computationally unrecoverable. Supports AWS KMS and HashiCorp Vault. Generates a deletion receipt attesting key deletion with key version ID, covering data categories where physical deletion is not feasible (Kafka topics, backup archives, log aggregators).

**From:** Chapters 15.2, 16.3

**Why open source:** Privacy authorities increasingly recognize cryptographic erasure as an acceptable form of deletion for data where physical deletion is architecturally impractical. A correct implementation is non-trivial: it requires key rotation support, audit of the key deletion event itself, and honest documentation in the privacy policy of what "deletion" means in this context.

---

## 11. `receipt-renderer` — Plain-Language Receipt Renderer

**What:** Takes a raw deletion receipt JSON and renders it as:
- A human-readable plain-language summary ("Your file uploaded on March 14 was permanently deleted at 10:31 AM. The file's unique fingerprint is included so you can confirm it refers to your specific document.")
- An HTML card suitable for embedding in a completion UI
- A PDF for compliance archival

Supports multiple languages; the underlying JSON canonical record is unchanged.

**From:** Chapter 13.4

**Why open source:** The gap between what a cryptographic artifact means technically and what a compliance officer, healthcare administrator, or end user can act on is a documented usability failure. A renderer bridges it without altering the canonical record — the plain-language layer translates the receipt, it does not replace it.

---

## 12. `deletion-scheduler` — TTL Policy Engine

**What:** Configurable TTL management layer: each data store (MongoDB collection, Postgres table, S3 prefix, Redis key pattern) is assigned a documented retention policy. A scheduler runs cleanup on configured intervals, identifies expired records, calls the deletion pipeline, and emits receipts. Separate cleanup path for failed jobs (upload event but no `processing_complete` after a configurable window).

**From:** Chapters 11.1–11.2, 16.2

**Why open source:** The book frames "deletion by default" as the emerging regulatory posture under GDPR Article 25 (privacy by design): every table must have a documented retention policy, and any data that lacks one must be treated as subject to immediate deletion. A standalone TTL engine enforcing this is the infrastructure primitive that makes deletion-by-default operational rather than aspirational.

---

## Already Published

`deleteceipt` v0.1.0 covers the core receipt issuance (items 1 and 2 partially):
- HMAC-SHA256 signing over canonical JSON
- ECDSA/P-256 variant (`pip install "deleteceipt[ecdsa]"`)
- MongoDB backend (`pip install "deleteceipt[mongo]"`)

The twelve items above are the remaining open surface area described in the book.
