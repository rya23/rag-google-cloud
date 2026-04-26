import json
from typing import Dict, List

import psycopg

from app.config import DATABASE_URL


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"


def fetch_similar_docs(vector: List[float], dim: int, k: int) -> List[Dict]:
    vector_col = "embedding_128" if dim == 128 else "embedding_768"
    vec_literal = _vector_literal(vector)

    query = f"""
        SELECT
            id,
            source,
            chunk_text,
            metadata,
            1 - ({vector_col} <=> %s::vector) AS similarity
        FROM documents
        WHERE {vector_col} IS NOT NULL
        ORDER BY {vector_col} <=> %s::vector
        LIMIT %s;
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (vec_literal, vec_literal, k))
            rows = cur.fetchall()

    results = []
    for row in rows:
        metadata = row[3]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        results.append(
            {
                "id": row[0],
                "source": row[1],
                "text": row[2],
                "metadata": metadata or {},
                "similarity": float(row[4]),
            }
        )
    return results


def upsert_embeddings_for_source(
    source: str, dim: int, vectors: List[List[float]]
) -> int:
    vector_col = "embedding_128" if dim == 128 else "embedding_768"

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM documents WHERE source = %s ORDER BY id ASC",
                (source,),
            )
            ids = [r[0] for r in cur.fetchall()]

            count = min(len(ids), len(vectors))
            for idx in range(count):
                vec_literal = _vector_literal(vectors[idx])
                cur.execute(
                    f"UPDATE documents SET {vector_col} = %s::vector WHERE id = %s",
                    (vec_literal, ids[idx]),
                )

        conn.commit()
    return count


def list_source_chunks(source: str) -> List[str]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chunk_text FROM documents WHERE source = %s ORDER BY id ASC",
                (source,),
            )
            rows = cur.fetchall()
    return [r[0] for r in rows]


def list_sources() -> List[str]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT source FROM documents ORDER BY source ASC")
            rows = cur.fetchall()
    return [r[0] for r in rows]
