from typing import Dict, List, Optional

import httpx
from groq import Groq
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app import config


def _auth_headers(audience: str) -> dict:
    if config.SERVICE_AUTH_MODE != "gcp_id_token":
        return {}

    token = id_token.fetch_id_token(Request(), audience)
    return {"Authorization": f"Bearer {token}"}


def _service_headers(
    base_url: str, extra_headers: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    headers = dict(extra_headers or {})
    headers.update(_auth_headers(base_url))
    return headers


async def embed_texts(texts: List[str], dim: int) -> List[List[float]]:
    last_error = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = _service_headers(config.EMBEDDING_SERVICE_URL)
                r = await client.post(
                    f"{config.EMBEDDING_SERVICE_URL}/embed",
                    json={"texts": texts, "dim": dim},
                    headers=headers,
                )
                r.raise_for_status()
                return r.json()["vectors"]
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"embedding_call_failed: {last_error}")


async def rerank(query: str, candidates: List[str]) -> List[dict]:
    last_error = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = _service_headers(config.RERANKER_SERVICE_URL)
                r = await client.post(
                    f"{config.RERANKER_SERVICE_URL}/rerank",
                    json={"query": query, "candidates": candidates},
                    headers=headers,
                )
                r.raise_for_status()
                return r.json()["ranked"]
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"reranker_call_failed: {last_error}")


async def create_ingestion_job(
    filename: str,
    raw: bytes,
    content_type: Optional[str] = None,
) -> dict:
    last_error = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = _service_headers(config.INGESTION_SERVICE_URL)
                files = {
                    "file": (
                        filename,
                        raw,
                        content_type or "application/octet-stream",
                    )
                }
                r = await client.post(
                    f"{config.INGESTION_SERVICE_URL}/ingest/file",
                    files=files,
                    headers=headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"ingestion_create_job_failed: {last_error}")


async def list_ingestion_jobs() -> dict:
    last_error = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = _service_headers(config.INGESTION_SERVICE_URL)
                r = await client.get(
                    f"{config.INGESTION_SERVICE_URL}/ingest/jobs",
                    headers=headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"ingestion_list_jobs_failed: {last_error}")


async def get_ingestion_job(job_id: int) -> dict:
    last_error = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = _service_headers(config.INGESTION_SERVICE_URL)
                r = await client.get(
                    f"{config.INGESTION_SERVICE_URL}/ingest/jobs/{job_id}",
                    headers=headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"ingestion_get_job_failed: {last_error}")


def generate_answer(query: str, contexts: List[str]) -> str:
    if not config.GROQ_API_KEY:
        return "GROQ_API_KEY is not set. Retrieved contexts are available in sources."

    prompt = (
        "You are a concise financial assistant. "
        "Answer using only the provided context. "
        "If context is insufficient, say so clearly.\n\n"
        f"Question: {query}\n\n"
        "Context:\n" + "\n\n".join([f"- {c}" for c in contexts])
    )

    client = Groq(api_key=config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "You answer with grounded, short responses."},
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content or ""
