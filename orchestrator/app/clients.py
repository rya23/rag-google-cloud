from typing import List

import httpx
from groq import Groq

from app import config


async def embed_texts(texts: List[str], dim: int) -> List[List[float]]:
    last_error = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    f"{config.EMBEDDING_SERVICE_URL}/embed",
                    json={"texts": texts, "dim": dim},
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
                r = await client.post(
                    f"{config.RERANKER_SERVICE_URL}/rerank",
                    json={"query": query, "candidates": candidates},
                )
                r.raise_for_status()
                return r.json()["ranked"]
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"reranker_call_failed: {last_error}")


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
