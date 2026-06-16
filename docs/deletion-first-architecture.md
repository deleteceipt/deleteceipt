# Deletion-First Architecture

The easiest data to delete is data that was never written to persistent storage in
the first place. Deletion-first architecture is the practice of designing systems
so that data expires, evaporates, or is scoped to transient storage by default —
reversing the implicit assumption that data, once created, persists until explicitly
removed.

## The Permanence Inversion

Traditional computing treats persistence as the default and deletion as an
exception. Databases store rows indefinitely unless purged. Filesystems write bytes
until explicitly erased. Logs accumulate until rotated. The developer has to
actively opt into deletion.

Deletion-first architecture inverts this: impermanence is the default, and
persistence must be explicitly justified. A system built this way produces less
data that needs to be deleted, because most data was never durably stored. The
right to be forgotten is easiest to honor when the system was designed from the
start to forget.

## Ephemeral Storage for Transient Data

For data that only needs to exist for the duration of a processing job, ephemeral
storage provides a strong architectural guarantee: the data cannot survive a
process restart.

On Linux, `tmpfs` is a RAM-backed filesystem mounted with:

```bash
mount -t tmpfs -o size=4g tmpfs /mnt/processing
```

Data written to a `tmpfs` mount lives in kernel memory (and swap, if enabled). It
disappears completely when the mount is unmounted or the system reboots. There is
no fsync to a persistent block device, no journal entry, no block allocation on
spinning or flash storage. The filesystem path is a lie, in the best sense: it
looks like a path but points at RAM.

In Kubernetes, the `emptyDir` volume with `medium: Memory` achieves the same
effect:

```yaml
volumes:
  - name: job-workspace
    emptyDir:
      medium: Memory
      sizeLimit: 2Gi
```

This volume is mounted into the pod's containers and destroyed when the pod
terminates — whether by completion, eviction, or restart. Files written to it
during the job lifecycle are gone before any external process could copy them.

The architectural guarantee is what enables a strong deletion receipt. A receipt
that says "the file was stored in `/mnt/processing/job-id/input.pdf` and then
deleted" is more credible when the filesystem at that path is RAM-backed and
disappears on reboot than when it refers to a persistent NFS mount. The storage
path in the receipt's `files_deleted` manifest is itself evidence about where the
data lived.

## TTL-by-Default

For data that requires persistence beyond a single process — session state, job
metadata, temporary outputs available for download — TTL (time-to-live) policies
are the deletion-first approach.

**Redis** supports per-key expiration natively:

```python
redis_client.setex("job:abc123:output", 3600, output_bytes)  # expires in 1 hour
```

The key is automatically removed after the TTL elapses. No background purge job
required. No soft-delete pattern. No risk that the purge job is deprioritized
under load.

**DynamoDB** supports table-level TTL via a designated timestamp attribute:

```python
item = {
    "job_id": job_id,
    "file_hash": file_hash,
    "ttl": int(time.time()) + 3600,  # Unix timestamp 1 hour from now
}
table.put_item(Item=item)
```

DynamoDB's TTL deletion is eventually consistent (typically within 48 hours of
expiry) and deletion events are propagated to DynamoDB Streams and AWS Lambda
triggers, enabling downstream cleanup workflows.

**Kafka** topic-level retention (`retention.ms`, `retention.bytes`) ensures that
messages older than the configured window are purged from the partition log. For
systems that use event streaming as the integration layer, this limits how long
personal data persists in the stream regardless of consumer behavior.

**PostgreSQL** does not have a built-in TTL mechanism, but a simple scheduled job
(`pg_cron` or an external scheduler) can enforce expiry:

```sql
DELETE FROM jobs WHERE expires_at < NOW();
```

The important discipline is making the expiry a property of the data model —
an `expires_at` column set at write time — rather than a secondary decision made
later. Data that has a defined lifespan from creation is far more reliably deleted
than data where deletion is retrofitted.

## Data Minimization

Collect only what the processing requires for the time it requires it. This
principle — a GDPR Article 5(1)(c) obligation — is also the most effective
technical defense against the persistence problem.

In a document processing context, data minimization means:

- Accept the file as an upload, process it, return the output, then delete both
- Do not retain the original file for "potential future reprocessing"
- Do not retain the output file after the user has downloaded it
- Do not extract metadata (document author, embedded GPS coordinates, revision
  history) unless the extraction is the explicit service being delivered
- Do not log request bodies containing file content

Every byte of user data that is not retained is a byte that cannot surface in a
backup, a search index, a log file, or a data breach. The most defensible deletion
record is one where the data's lifecycle was short by design.

## Data Isolation: One Job, One Directory

When multiple users' data is processed on shared infrastructure, mixing creates
risk: bugs that affect one job can leak into adjacent jobs; a path traversal
vulnerability in one job can reach another job's files; cleanup logic that misses
a subdirectory in one job may miss data for a different user.

The isolation pattern is simple: each processing job receives its own directory,
scoped to that job's ID:

```
/mnt/processing/
  f47ac10b-58cc-4372-a567-0e02b2c3d479/    # job UUID
    input.pdf
    output.pdf
    text_layer.txt
```

Cleanup deletes the entire directory by job ID:

```python
import shutil
shutil.rmtree(f"/mnt/processing/{job_id}")
```

A single `rmtree` call removes all files associated with the job — input, output,
and intermediates. There is no list of specific files to enumerate and no risk of
missing a file the cleanup code did not know about. The directory structure is the
manifest.

This pattern also enables the `files_deleted` manifest in a deletion receipt to be
constructed automatically by listing the directory contents immediately before
deletion. The manifest is derived from the actual filesystem state, not from a
manually maintained list of expected files.

## Putting It Together

A deletion-first system for file processing might look like this:

1. Receive the file upload into a `tmpfs` path under a job-scoped directory
2. Compute the SHA-256 hash immediately and store it in the database (the
   pre-deletion commitment)
3. Process the file; all artifacts go into the same job directory
4. Return the output to the user; delete the job directory and issue the receipt
5. Store only the receipt and the hash in durable storage — not the file

In this architecture, persistent storage never holds the file content. The file
existed only in RAM. The window between upload and deletion is the processing
time, not an unbounded retention period. The receipt documents what was where.

This is not just good privacy practice — it is also a simpler system. Fewer
persistent copies means fewer places to look for bugs, fewer consistency problems,
and smaller backup sizes. The deletion-first architecture pays for itself in
operational simplicity even before the privacy benefits are counted.
