from typing import List

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.config import EMBEDDING_SERVICE_URL, SERVICE_AUTH_MODE


def _auth_headers(audience: str) -> dict:
    if SERVICE_AUTH_MODE != "gcp_id_token":
        return {}

    token = id_token.fetch_id_token(Request(), audience)
    return {"Authorization": f"Bearer {token}"}


async def embed_texts(texts: List[str], dim: int) -> List[List[float]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = _auth_headers(EMBEDDING_SERVICE_URL)
        r = await client.post(
            f"{EMBEDDING_SERVICE_URL}/embed",
            json={"texts": texts, "dim": dim},
            headers=headers,
        )
        r.raise_for_status()
        return r.json()["vectors"]
