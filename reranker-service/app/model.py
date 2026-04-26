import os
from functools import lru_cache
from typing import List

from sentence_transformers import CrossEncoder


MODEL_ID = os.getenv("RERANKER_MODEL_ID", "cross-encoder/ms-marco-MiniLM-L-6-v2")


@lru_cache(maxsize=1)
def get_model() -> CrossEncoder:
    return CrossEncoder(MODEL_ID)


def rerank(query: str, candidates: List[str]) -> List[float]:
    model = get_model()
    pairs = [[query, c] for c in candidates]
    scores = model.predict(pairs)
    return [float(s) for s in scores]
