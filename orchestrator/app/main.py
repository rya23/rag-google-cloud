from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import config
from app.clients import embed_texts
from app.db import list_source_chunks, list_sources, upsert_embeddings_for_source
from app.graph import build_graph
from app.seed import run_seed


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    k: Optional[int] = None


class SourceItem(BaseModel):
    id: int
    source: str
    text: str
    score: float
    metadata: Dict[str, Any]


class QueryResponse(BaseModel):
    answer: str
    path_used: str
    top_score: float
    sources: List[SourceItem]


class IngestRequest(BaseModel):
    source: str = Field(min_length=1)


app = FastAPI(title="orchestrator")
graph = build_graph()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "orchestrator"}


@app.post("/seed")
def seed() -> dict:
    run_seed()
    return {"status": "ok"}


@app.post("/ingest/source")
async def ingest_source(req: IngestRequest) -> dict:
    chunks = list_source_chunks(req.source)
    if not chunks:
        raise HTTPException(status_code=404, detail="source_not_found")

    vectors_128 = await embed_texts(chunks, 128)
    vectors_768 = await embed_texts(chunks, 768)

    updated_128 = upsert_embeddings_for_source(req.source, 128, vectors_128)
    updated_768 = upsert_embeddings_for_source(req.source, 768, vectors_768)

    return {
        "source": req.source,
        "updated_128": updated_128,
        "updated_768": updated_768,
    }


@app.post("/ingest/all")
async def ingest_all() -> dict:
    results = []
    for source in list_sources():
        chunks = list_source_chunks(source)
        if not chunks:
            continue
        vectors_128 = await embed_texts(chunks, 128)
        vectors_768 = await embed_texts(chunks, 768)
        updated_128 = upsert_embeddings_for_source(source, 128, vectors_128)
        updated_768 = upsert_embeddings_for_source(source, 768, vectors_768)
        results.append(
            {
                "source": source,
                "updated_128": updated_128,
                "updated_768": updated_768,
            }
        )
    return {"sources": results}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    k = req.k or config.DEFAULT_TOP_K
    try:
        state = await graph.ainvoke({"query": req.query, "k": k})
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"orchestration_failed: {exc}"
        ) from exc

    docs = state.get("reranked", [])[:k]
    sources = [
        SourceItem(
            id=d["id"],
            source=d["source"],
            text=d["text"],
            score=float(d.get("rerank_score", d.get("similarity", 0.0))),
            metadata=d.get("metadata", {}),
        )
        for d in docs
    ]

    return QueryResponse(
        answer=state.get("answer", ""),
        path_used=state.get("path_used", "unknown"),
        top_score=float(state.get("rerank_top_score", 0.0)),
        sources=sources,
    )
