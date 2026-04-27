import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg

from app.config import DATABASE_URL


def _now() -> datetime:
    return datetime.utcnow()


def create_job(filename: str, storage_path: str) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingestion_jobs (filename, storage_path, status, attempts, created_at)
                VALUES (%s, %s, 'pending', 0, %s)
                RETURNING id
                """,
                (filename, storage_path, _now()),
            )
            job_id = cur.fetchone()[0]
        conn.commit()
    return int(job_id)


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, storage_path, status, error, attempts, created_at, started_at, completed_at
                FROM ingestion_jobs
                WHERE id = %s
                """,
                (job_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "storage_path": row[2],
        "status": row[3],
        "error": row[4],
        "attempts": row[5],
        "created_at": row[6],
        "started_at": row[7],
        "completed_at": row[8],
    }


def list_recent_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, status, error, attempts, created_at, completed_at
                FROM ingestion_jobs
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "status": r[2],
            "error": r[3],
            "attempts": r[4],
            "created_at": r[5],
            "completed_at": r[6],
        }
        for r in rows
    ]


def claim_pending_job(max_attempts: int) -> Optional[Dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, storage_path, attempts
                FROM ingestion_jobs
                WHERE status = 'pending' AND attempts < %s
                ORDER BY id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,
                (max_attempts,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None

            cur.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'processing', attempts = attempts + 1, started_at = %s, error = NULL
                WHERE id = %s
                """,
                (_now(), row[0]),
            )
        conn.commit()

    return {
        "id": row[0],
        "filename": row[1],
        "storage_path": row[2],
        "attempts": row[3] + 1,
    }


def mark_job_done(job_id: int) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'completed', completed_at = %s
                WHERE id = %s
                """,
                (_now(), job_id),
            )
        conn.commit()


def mark_job_failed(job_id: int, error: str, attempts: int, max_attempts: int) -> None:
    final_status = "failed" if attempts >= max_attempts else "pending"
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ingestion_jobs
                SET status = %s,
                    error = %s,
                    completed_at = CASE WHEN %s = 'failed' THEN %s ELSE completed_at END
                WHERE id = %s
                """,
                (final_status, error[:1000], final_status, _now(), job_id),
            )
        conn.commit()


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"


def insert_document_chunks(
    *,
    source: str,
    filename: str,
    job_id: int,
    chunks: List[str],
    vectors_128: List[List[float]],
    vectors_768: List[List[float]],
) -> int:
    inserted = 0
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for idx, chunk in enumerate(chunks):
                metadata = json.dumps({"filename": filename, "job_id": job_id})
                cur.execute(
                    """
                    INSERT INTO documents (
                        source,
                        filename,
                        job_id,
                        chunk_index,
                        chunk_text,
                        metadata,
                        embedding_128,
                        embedding_768
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s::jsonb, %s::vector, %s::vector
                    )
                    """,
                    (
                        source,
                        filename,
                        job_id,
                        idx,
                        chunk,
                        metadata,
                        _vector_literal(vectors_128[idx]),
                        _vector_literal(vectors_768[idx]),
                    ),
                )
                inserted += 1
        conn.commit()
    return inserted
