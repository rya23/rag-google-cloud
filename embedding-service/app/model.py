import os
from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer


MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "rya23/modernbert-embed-finance-matryoshka")


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_ID)


def embed_texts(texts: List[str], dim: int) -> List[List[float]]:
    model = get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        truncate_dim=dim,
    )
    return vectors.tolist()
