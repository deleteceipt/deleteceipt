# GDPR Deletion Compliance Checker

## Concept

A self-assessment platform for Data Protection Officers and security officers at any IT service provider to evaluate their GDPR Article 17 deletion compliance — and receive a cryptographically signed, dated compliance report they can present to regulators, auditors, and enterprise customers.

Not a legal checklist. A **technical** assessment grounded in the actual deletion architecture the book describes: storage layers, TTL pipelines, audit logs, receipt issuance, backup conflicts, Kafka strategies, ML model governance.

No existing GDPR checker goes to this depth on the deletion pipeline specifically.

---

## Positioning

> **"The only GDPR compliance checker built by engineers, for engineers."**

Most GDPR tools ask whether you have a privacy policy. This one asks whether your Elasticsearch index has a deletion hook wired to your primary store, whether your Kafka topics use field-level encryption with key deletion, and whether your deletion receipts survive a signature verification check run independently of the platform that issued them.

---

## Scoring Model: 4-Level Maturity

Every control is scored on a maturity scale rather than binary pass/fail. This produces a roadmap, not just a verdict — and a regulator seeing "implemented but not tested" treats it more credibly than an unexplained "partial."

| Level | Label | Meaning |
|---|---|---|
| 0 | **None** | Control does not exist; gap is open |
| 1 | **Documented** | Policy or design exists on paper; not yet implemented in code |
| 2 | **Implemented** | Code or infrastructure change is live in production |
| 3 | **Tested** | Automated tests verify the control works; CI runs on every deploy |
| 4 | **Monitored** | Continuous monitoring with alerting; reconciliation jobs catch regressions |

Overall score = weighted average across all controls, expressed as a percentage and a maturity tier (Foundational / Developing / Advanced / Exemplary).

---

## Industry Verticals

The officer selects their sector at the start. The questionnaire weights controls by regulatory priority for that sector, and the report includes the relevant cross-framework mapping.

| Vertical | Additional Framework Mapped |
|---|---|
| **General SaaS** | SOC 2 Type II (deletion and disposal control domain) |
| **Healthcare** | HIPAA Privacy Rule + Security Rule (6-year documentation requirement) |
| **Financial Services** | SEC Rules 17a-3/17a-4, FINRA, MiFID II (retention vs. erasure conflict analysis) |
| **Legal Services** | State bar rules, professional responsibility standards, client confidentiality obligations |
| **Public Sector / EU** | EDPB guidance, national DPA interpretations, ePrivacy Directive |

---

## Assessment Structure

### Section 1 — Primary Storage Deletion
*Source: Chapter 15.1*

- Does your database physically remove rows, or use soft deletes (`deleted_at` timestamp)?
- If soft deletes: is there a hard-delete pipeline running on a defined schedule?
- Is the hard-delete pipeline monitored and alarmed?
- Does it cover all tables and collections holding personal data, or only the ones the original developer remembered?

**Controls scored:** hard delete implementation, soft-delete pipeline, coverage completeness, monitoring

---

### Section 2 — Search and Derived Indexes
*Source: Chapter 15.1*

- Do you index personal data in Elasticsearch, OpenSearch, Solr, or a similar system?
- Does your deletion pipeline explicitly call the index's delete API?
- Does it handle the case where indexing was asynchronous and the document may not yet exist in the index at deletion time?

**Controls scored:** index deletion hook, async propagation handling, verification after deletion

---

### Section 3 — Cache Invalidation
*Source: Chapter 15.1*

- Do Redis, Memcached, or application-layer caches hold personal data?
- TTL-based expiry is probabilistic, not guaranteed — does your deletion pipeline explicitly invalidate or overwrite cache entries keyed to the deleted user?

**Controls scored:** explicit cache invalidation, key pattern coverage, TTL policy documentation

---

### Section 4 — Message Queues and Event Streams
*Source: Chapter 15.1*

- Do Kafka topics, SQS queues, or Kinesis streams hold events containing personal data?
- Kafka does not support record-level deletion in most configurations — have you evaluated compacted topics, field-level encryption with key deletion, or dedicated erasure topics?
- What is your maximum retention window for personal data in event streams?

**Controls scored:** stream deletion strategy, field-level encryption implementation, retention window documentation

---

### Section 5 — Backup and Archive Storage
*Source: Chapter 14.3*

- What is your maximum residual retention period for personal data in backups?
- Is this period documented in your deletion response communications to data subjects?
- Do you have a process — even a manual one — for eventually removing deleted records from restored backups?
- When a legal hold is lifted, does your backup purge process account for data that was preserved under the hold?

**Controls scored:** backup retention policy documentation, purge process existence, legal hold interaction, communication to data subjects

---

### Section 6 — Logs and Observability Data
*Source: Chapter 15.1*

- Do application logs, access logs, or distributed tracing data contain personal information (IP addresses, user identifiers, request parameters, error messages containing user input)?
- Does your logging infrastructure support record-level deletion, or do you rely on log rotation?
- Have you applied log-level anonymization at ingestion?
- What are your retention windows for raw log data?

**Controls scored:** PII in logs inventory, anonymization at ingestion, retention window, record-level deletion capability

---

### Section 7 — Third-Party Processors
*Source: Chapter 15.1*

- For each SaaS tool in your stack (CRM, analytics, error tracking, customer support), do you send deletion requests when a user's data must be erased?
- Do you have contractual confirmation that each processor honors those requests?
- Do you have any verification mechanism — a receipt, a confirmation, an audit log entry — that the processor acted on the request?

**Controls scored:** processor inventory completeness, deletion request propagation, contractual coverage, verification mechanism

---

### Section 8 — Machine Learning Models
*Source: Chapters 14.1, 14.4*

- Have you trained models on personal data that may include data subjects who later exercise their erasure right?
- Do you have a disclosed policy for what "deletion" means with respect to model weights?
- Have you evaluated machine unlearning, retraining schedules that exclude deleted users' data, or differential privacy during training?
- Is the distinction between file-level deletion (documented by receipt) and model influence (not fully reversible) clearly disclosed to data subjects?

**Controls scored:** training data inventory, disclosure of model data use, unlearning or exclusion mechanism, honest documentation of limits

---

### Section 9 — Deletion Receipt Issuance
*Source: Chapters 9–11*

- Do you issue a cryptographically signed deletion receipt at the time of deletion?
- Does the receipt include: job/request identifier, file hash, upload timestamp, deletion timestamp, manifest of deleted files with roles, and a server signature?
- Is the signature computed over canonical JSON (sorted keys, no whitespace) to ensure deterministic verification?
- Is the signing key stored in a dedicated secrets manager (not in code or environment variables in plaintext)?
- Is key rotation automated on a defined schedule, with historical keys retained for verification of old receipts?

**Controls scored:** receipt issuance, receipt schema completeness, canonical JSON signing, key management maturity, key rotation

---

### Section 10 — Audit Log Integrity
*Source: Chapter 10*

- Do you maintain an append-only audit log of deletion events?
- Is the log hash-chained so that tampering with any entry is detectable?
- Is the audit log separated from your operational database by access controls?
- Can you run a chain verification check on demand?

**Controls scored:** audit log existence, hash chaining, access control separation, verification capability

---

### Section 11 — Legal Hold Procedures
*Source: Chapter 14.3*

- Do you have a process for placing legal holds that suspend normal deletion routines?
- When a file cannot be deleted due to a legal hold, do you issue a hold notification document (rather than a deletion receipt) that records the hold's existence and reason?
- When a hold is lifted, do you re-queue deletion and issue a receipt annotated with the hold period?
- Can you respond to a data subject's erasure request explaining that deletion cannot proceed without disclosing the existence of the proceeding?

**Controls scored:** hold suspension mechanism, hold notification issuance, post-hold deletion, data subject communication procedure

---

### Section 12 — Federated and Multi-Node Systems
*Source: Chapter 14.2*

- Is your architecture single-node, or do documents flow across multiple processing nodes, regional deployments, or partner systems?
- For federated architectures: does your deletion pipeline initiate deletion across all nodes and collect acknowledgment from each before issuing a receipt?
- Does your receipt enumerate which nodes participated in the deletion event?
- Do you have a reconciliation mechanism for nodes that were unreachable at deletion time?

**Controls scored:** federation map accuracy, distributed deletion coordination, per-node acknowledgment, unreachable node reconciliation

---

### Section 13 — Cryptographic Erasure for Residual Data
*Source: Chapters 15.2, 16.3*

- For data categories where physical deletion is not feasible (Kafka, backups, log aggregators), do you use per-user encryption with key deletion as cryptographic erasure?
- Is the key management system (KMS) separate from the data it protects?
- Is key deletion itself audited and documented?
- Is the use of cryptographic erasure (rather than physical deletion) disclosed to data subjects and documented in your privacy policy?

**Controls scored:** crypto-shredding implementation, KMS separation, key deletion audit, honest disclosure

---

### Section 14 — Deletion Testing and Continuous Verification
*Source: Chapter 15.5*

- Do you have automated integration tests that verify deletion across each storage layer against real infrastructure (not mocks)?
- Do these tests run in CI on every deploy?
- Do you run a scheduled "deletion audit" job that samples recently fulfilled deletion requests and queries each storage layer to confirm data is absent?
- Do you have a shell-level or out-of-band verification script for incident response?

**Controls scored:** integration test coverage, CI integration, scheduled audit job, out-of-band verification

---

## Output: The Compliance Report

### What the officer receives

1. **Maturity scorecard** — per-section scores (0–4) and overall weighted score by vertical
2. **Gap analysis** — controls at level 0 or 1, ranked by regulatory risk exposure
3. **Remediation roadmap** — prioritized action items with effort estimates and references to the specific book chapter and open source component that addresses each gap
4. **Cross-framework mapping** — how each control maps to their selected vertical (HIPAA, SOC 2, SEC, etc.)
5. **Plain-language executive summary** — suitable for a board or legal team, non-technical
6. **Signed compliance artifact** — JSON + PDF, HMAC-SHA256 signed and timestamped, with a `schema_version`, `assessment_id`, `organization_id` (anonymized), `completed_at`, and `report_version`

### The signed artifact

```json
{
  "payload": {
    "assessment_id": "assess_7f3a2c1d-9b4e-4f8a-b2e1-7c3d5a9f0e6b",
    "organization_id": "org_anonymized_hash",
    "completed_at": "2025-06-17T14:30:00Z",
    "vertical": "healthcare",
    "overall_score": 61,
    "maturity_tier": "Developing",
    "section_scores": {
      "primary_storage": 3,
      "search_indexes": 2,
      "cache_invalidation": 2,
      "message_queues": 1,
      "backup_archive": 1,
      "logs_observability": 2,
      "third_party_processors": 1,
      "ml_models": 0,
      "deletion_receipt_issuance": 0,
      "audit_log_integrity": 1,
      "legal_hold_procedures": 1,
      "federated_systems": 2,
      "cryptographic_erasure": 0,
      "deletion_testing": 1
    },
    "critical_gaps": [
      "deletion_receipt_issuance",
      "ml_models",
      "cryptographic_erasure"
    ],
    "schema_version": "1.0"
  },
  "signature": "9xK4mP2qR7sT1uV5wXlyZ8aB3cD6eF0gH2iJ5kL7mN9oP1qR3sT6uVOwX4yZ8=",
  "signing_key_id": "compliance-checker-signing-key/v1/2025-06-01"
}
```

The signed artifact can be:
- Retained privately as an internal compliance record
- Shared with enterprise customers as vendor management evidence
- Presented to a DPA or auditor as a self-assessment with a verifiable timestamp
- Re-run after remediation to show progress — each assessment is independently signed and dated

---

## Remediation Roadmap Format

Each critical gap links directly to the open source component that addresses it:

| Gap | Risk Level | Effort | Open Source Component | Reference |
|---|---|---|---|---|
| No deletion receipt issuance | Critical | Medium | `deleteceipt` v0.1.0 | Ch. 9–11 |
| No ML model data governance disclosure | High | Low | Policy + `deletion-inventory` | Ch. 14.1, 14.4 |
| No cryptographic erasure for Kafka/backups | High | High | `crypto-shredder` | Ch. 15.2, 16.3 |
| Backup purge process undocumented | High | Low | Policy documentation | Ch. 14.3 |
| No third-party processor verification | Medium | Medium | `deleteceipt-enterprise` | Ch. 15.1 |
| Deletion pipeline untested | Medium | Medium | `deletion-audit-test` | Ch. 15.5 |
| No audit log hash chaining | Medium | Medium | `deleteceipt-audit` | Ch. 10 |
| Legal hold procedure missing | Medium | Medium | `legal-hold-gate` | Ch. 14.3 |

---

## What Makes This Different

| Existing GDPR checkers | This tool |
|---|---|
| Written by lawyers for lawyers | Written by engineers for engineers |
| Ask about policies and consent mechanisms | Ask about TTL pipelines, hash chaining, Kafka strategies |
| Binary pass/fail | 4-level maturity with a roadmap |
| Generic output | Sector-weighted scoring with cross-framework mapping |
| No remediation path | Every gap links to an open source component |
| No verifiable artifact | HMAC-signed, timestamped, independently verifiable report |
| One-time assessment | Re-assessment tracks progress over time |

---

## Implementation Stack

- **Frontend:** Single-page questionnaire with branching logic by vertical; progress saved in session
- **Backend:** Python / FastAPI; scoring engine reads a YAML control definition file (auditable, version-controlled)
- **Report generation:** `receipt-renderer` pattern — JSON canonical record + PDF render
- **Signing:** Same HMAC-SHA256 + canonical JSON pattern as `deleteceipt`; key stored in AWS Secrets Manager
- **Storage:** Anonymized assessment results only; no organization name or identifying information stored server-side
- **Verification:** Public `verify_assessment.py` CLI — officer can verify their signed report independently at any time

---

## Connection to the Broader Ecosystem

The compliance checker is the **entry point** to the deleteceipt ecosystem:

1. Officer runs the assessment → discovers they have no deletion receipt issuance (level 0)
2. Remediation roadmap points to `deleteceipt` v0.1.0
3. They integrate `deleteceipt` → re-run assessment → score moves to level 2
4. They add integration tests using `deletion-audit-test` → score moves to level 3
5. They deploy `deleteceipt-reconcile` with monitoring → score moves to level 4
6. They export their receipts using `deleteceipt-enterprise` → present to their own enterprise customers as vendor evidence

The checker is not just a diagnostic — it is a curriculum that walks an organization from zero to exemplary deletion compliance, with open source tools at every step.
