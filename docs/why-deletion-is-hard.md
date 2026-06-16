# Why Deletion Is Hard: The Technical Reality

Deletion is the most misunderstood operation in computing. Users think of it as
removal. Systems treat it as metadata modification. The gap between those two
definitions is where data persists long after a user believes it is gone.

## The Filesystem Illusion

Modern filesystems do not erase data when you delete a file. They mark the inode
as free and update the directory entry — but the bytes remain on disk until the
block allocator happens to reuse them for a new file. On ext4 and most other
Linux filesystems, `rm` is semantically closer to "unlink" than to "erase."

SSDs compound this. Flash storage uses a Flash Translation Layer (FTL) that
remaps logical block addresses to physical flash cells. When a block is "deleted,"
the FTL marks it as available for reuse but does not immediately erase the
physical cell — that requires a dedicated erase cycle that the drive manages
asynchronously. Wear-leveling algorithms may move data to different physical
locations, leaving copies scattered across cells. The `TRIM` command signals to
the SSD that blocks can be erased, but execution timing is under drive firmware
control, not the OS.

The practical implication: "deleted" data on both HDDs and SSDs may be fully
recoverable with forensic tools for minutes, hours, or indefinitely, depending on
write pressure and drive behavior.

## Soft Deletes and the Tombstone Pattern

Most production databases do not perform hard deletes. The standard pattern is a
`deleted_at` timestamp column (or `is_deleted` boolean) that marks rows as
logically removed while leaving them physically present. Queries add
`WHERE deleted_at IS NULL` to exclude them; the rows remain visible to anyone
who queries without that filter, including:

- Background jobs that forget the filter
- Direct database connections used for debugging
- Analytics pipelines running against full table exports
- Data warehouse copies made before the soft delete

A purge job eventually removes soft-deleted rows, but purge schedules are often
daily or weekly, and may be deprioritized under load. In some systems, purge jobs
are never implemented at all — the "temporary" soft delete becomes permanent
storage.

## Write-Ahead Logs and Replication

Database write-ahead logs (WAL) record every write before it is applied, enabling
crash recovery and streaming replication. A row deleted from the primary database
at time T may persist in:

- The WAL on the primary until it is rotated
- The replication stream between primary and replica
- Read replicas that have not yet replayed the deletion
- Point-in-time recovery (PITR) backups that snapshot WAL positions

For compliance purposes, all of these are copies of the data. GDPR's right to
erasure applies to all copies, not just the primary database row.

## Backups

Backups are the most common reason deletion fails in practice. A nightly backup
taken before a deletion request means that even if the primary database is
perfectly purged, the backup contains the data. Backup retention policies of 30,
60, or 90 days are common; the user's data may persist in archived backups for
years.

Proper erasure requires either restoring and re-purging each relevant backup (which
is operationally expensive and sometimes technically infeasible) or accepting that
backup-resident copies exist and documenting them. Some regulations permit an
exception for backups, provided the data is excluded from the next backup cycle
and the backup is destroyed on its normal schedule. This exception has
prerequisites that many organizations do not meet: a documented backup retention
policy, a way to track which backups contain which user's data, and a process for
excluding data from the next backup.

## Caches, Search Indices, and Derived Data

Data flows beyond the primary database in ways that are often not tracked:

- **CDN caches**: User-generated content served via CDN may be cached at edge
  nodes with independent TTLs.
- **Search indices**: Elasticsearch, Solr, or Typesense indices built from database
  content do not automatically update when the source row is deleted.
- **Analytics aggregates**: Row-level data summarized into statistics or dashboards
  may encode the original values without retaining the raw row.
- **Machine learning models**: Models trained on user data encode statistical
  patterns from that data. "Deleting" the training record does not remove its
  influence from the model weights — a problem known as machine unlearning, which
  remains an active research area.
- **Event logs**: Application logs, access logs, and error logs often capture
  request payloads including personal data. These logs are typically retained for
  months for debugging and security purposes.

## What This Means for `deleteceipt`

A deletion receipt issued by `deleteceipt` describes what the issuing system
deleted from the storage it controls. It does not — and cannot — attest to copies
in systems the workflow did not integrate with. The signature says "this workflow
processed this deletion"; it does not say "this data has been erased from every
location in which it ever existed."

This is not a limitation of `deleteceipt` specifically. It is the fundamental
epistemological limit of any self-reported deletion proof: proving that data has
been deleted everywhere requires knowing everywhere it exists, which requires a
complete and accurate data inventory, which must itself be maintained with the same
rigor as the deletion workflow.

The honest posture is layered: fix the architecture to minimize persistence (see
[deletion-first-architecture.md](deletion-first-architecture.md)), implement
deletion workflows with full scope coverage, issue cryptographic receipts for what
the workflow covers, and document what it does not cover. Cryptography secures the
evidence. The architecture determines what the evidence can honestly claim.
