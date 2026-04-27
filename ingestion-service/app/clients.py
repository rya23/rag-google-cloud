from typing import List

import httpx

from app.config import EMBEDDING_SERVICE_URL


async def embed_texts(texts: List[str], dim: int) -> List[List[float]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{EMBEDDING_SERVICE_URL}/embed",
            json={"texts": texts, "dim": dim},
        )
        r.raise_for_status()
        return r.json()["vectors"]
