from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.model import embed_texts, get_model


class EmbedRequest(BaseModel):
    texts: List[str] = Field(min_length=1)
    dim: Literal[128, 768]


class EmbedResponse(BaseModel):
    vectors: List[List[float]]


app = FastAPI(title="embedding-service")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "embedding",
        "model_loaded": get_model.cache_info().currsize > 0,
    }


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    try:
        vectors = embed_texts(req.texts, req.dim)
        return EmbedResponse(vectors=vectors)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"embedding_failed: {exc}") from exc
