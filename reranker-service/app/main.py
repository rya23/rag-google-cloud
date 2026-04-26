from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.model import get_model, rerank


class RerankRequest(BaseModel):
    query: str = Field(min_length=1)
    candidates: List[str] = Field(min_length=1)


class RerankedItem(BaseModel):
    text: str
    score: float


class RerankResponse(BaseModel):
    ranked: List[RerankedItem]


app = FastAPI(title="reranker-service")


@app.on_event("startup")
def startup() -> None:
    get_model()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "reranker"}


@app.post("/rerank", response_model=RerankResponse)
def rerank_endpoint(req: RerankRequest) -> RerankResponse:
    try:
        scores = rerank(req.query, req.candidates)
        ranked = sorted(
            [
                RerankedItem(text=text, score=score)
                for text, score in zip(req.candidates, scores, strict=True)
            ],
            key=lambda item: item.score,
            reverse=True,
        )
        return RerankResponse(ranked=ranked)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"rerank_failed: {exc}") from exc
