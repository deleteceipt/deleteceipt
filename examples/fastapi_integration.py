# pip install fastapi uvicorn deleteceipt[ecdsa]
"""FastAPI integration example for deleteceipt.

Demonstrates a minimal document-processing service that:
  1. Accepts file uploads, computes and commits the SHA-256 hash immediately.
  2. Accepts a delete request, issues a cryptographically signed receipt.
  3. Serves the signed receipt as JSON.

Everything is in-memory — swap the dicts for a real database in production.

Run with:
    uvicorn fastapi_integration:app --reload
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from deleteceipt import compute_file_hash
from deleteceipt.ecdsa_receipt import generate_keypair, issue_receipt_ecdsa, verify_receipt_ecdsa

app = FastAPI(title="deleteceipt demo service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory "database"
# ---------------------------------------------------------------------------

# job_id -> {file_hash, filename, size_bytes, uploaded_at, body}
_jobs: dict[str, dict] = {}

# job_id -> signed receipt dict
_receipts: dict[str, dict] = {}

# Server keypair (generated once at startup — in production, load from secrets)
_PRIVATE_KEY_PEM, _PUBLIC_KEY_PEM = generate_keypair()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/upload", summary="Upload a file and receive a job ID")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Receive a file, compute its SHA-256 hash immediately (pre-deletion
    commitment), and store the job.

    The hash is committed HERE, at upload time, not at deletion time.
    That commitment is what makes the later receipt trustworthy.
    """
    body = await file.read()
    file_hash = compute_file_hash(body)  # committed before any processing

    import uuid
    job_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc)

    _jobs[job_id] = {
        "file_hash": file_hash,
        "filename": file.filename or "unknown",
        "size_bytes": len(body),
        "uploaded_at": uploaded_at,
        "body": body,  # in production: store to object storage, not memory
    }

    return {
        "job_id": job_id,
        "file_hash_sha256": file_hash,
        "uploaded_at": uploaded_at.isoformat(),
        "message": "File received. Hash committed. Ready to process.",
    }


@app.post("/jobs/{job_id}/delete", summary="Delete files and issue a signed receipt")
async def delete_job(job_id: str) -> dict:
    """Delete all files associated with a job and issue an ECDSA-signed
    deletion receipt.

    The receipt includes:
      - The file hash committed at upload time (not now — that's the point)
      - Timestamps for upload, processing, and deletion
      - An ECDSA/P-256 signature verifiable with the embedded public key
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found.")

    if job_id in _receipts:
        raise HTTPException(status_code=409, detail="Job already deleted.")

    processing_completed_at = datetime.now(timezone.utc)
    deleted_at = datetime.now(timezone.utc)

    # Issue the receipt BEFORE discarding the in-memory bytes
    receipt = issue_receipt_ecdsa(
        job_id=job_id,
        file_hash=job["file_hash"],
        uploaded_at=job["uploaded_at"],
        processing_completed_at=processing_completed_at,
        deleted_at=deleted_at,
        private_key_pem=_PRIVATE_KEY_PEM,
        files_deleted=[
            {
                "path": job["filename"],
                "size_bytes": job["size_bytes"],
                "role": "input",
            }
        ],
    )

    # "Delete" the file (discard bytes from memory)
    job.pop("body", None)
    _receipts[job_id] = receipt

    return {
        "message": "Files deleted. Receipt issued.",
        "job_id": job_id,
        "receipt_url": f"/jobs/{job_id}/receipt",
    }


@app.get("/jobs/{job_id}/receipt", summary="Download the signed deletion receipt")
async def get_receipt(job_id: str) -> JSONResponse:
    """Return the signed deletion receipt for a completed job.

    The receipt is self-contained: any party with the embedded public key
    can verify the signature without contacting this server.
    """
    receipt = _receipts.get(job_id)
    if not receipt:
        raise HTTPException(
            status_code=404,
            detail=f"No receipt for job {job_id!r}. Has it been deleted yet?",
        )
    return JSONResponse(content=receipt)


@app.get("/public-key", summary="Retrieve the server's ECDSA public key")
async def get_public_key() -> dict:
    """Return the server's P-256 public key for out-of-band receipt verification."""
    return {"public_key_pem": _PUBLIC_KEY_PEM}


@app.post("/verify-receipt", summary="Verify a receipt against the server public key")
async def verify_receipt_endpoint(receipt: dict) -> dict:
    """Convenience endpoint: verify a receipt JSON body.

    In practice, verifiers can do this locally using only the public key.
    """
    valid = verify_receipt_ecdsa(receipt, public_key_pem=_PUBLIC_KEY_PEM)
    return {"valid": valid}
