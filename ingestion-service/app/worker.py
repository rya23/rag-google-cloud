import asyncio
import argparse
from pathlib import Path

from app import config
from app.chunking import chunk_text
from app.clients import embed_texts
from app.db import (
    claim_pending_job,
    insert_document_chunks,
    mark_job_done,
    mark_job_failed,
)


def _source_from_filename(filename: str) -> str:
    base = Path(filename).stem.lower().strip()
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in base)
    return safe or "uploaded-doc"


async def process_job(job: dict) -> None:
    path = Path(job["storage_path"])
    if not path.exists():
        raise FileNotFoundError(f"missing_upload: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_text(text, config.INGEST_CHUNK_SIZE, config.INGEST_CHUNK_OVERLAP)
    if not chunks:
        raise ValueError("empty_document_after_chunking")

    vectors_128 = []
    vectors_768 = []

    batch_size = max(1, config.INGEST_BATCH_SIZE)
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        v128 = await embed_texts(batch, 128)
        v768 = await embed_texts(batch, 768)
        vectors_128.extend(v128)
        vectors_768.extend(v768)

    source = _source_from_filename(job["filename"])
    inserted = insert_document_chunks(
        source=source,
        filename=job["filename"],
        job_id=job["id"],
        chunks=chunks,
        vectors_128=vectors_128,
        vectors_768=vectors_768,
    )
    if inserted == 0:
        raise RuntimeError("no_rows_inserted")


async def run_worker(run_once: bool = False) -> None:
    while True:
        job = claim_pending_job(config.INGEST_MAX_ATTEMPTS)
        if not job:
            if run_once:
                return
            await asyncio.sleep(config.INGEST_POLL_INTERVAL_SEC)
            continue

        try:
            await process_job(job)
            mark_job_done(job["id"])
        except Exception as exc:
            mark_job_failed(
                job_id=job["id"],
                error=str(exc),
                attempts=job["attempts"],
                max_attempts=config.INGEST_MAX_ATTEMPTS,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process all currently pending jobs and exit",
    )
    args = parser.parse_args()
    asyncio.run(run_worker(run_once=args.once))
