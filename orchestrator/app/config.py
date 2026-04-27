import os
from typing import List


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5432/ragdb")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8010")
RERANKER_SERVICE_URL = os.getenv("RERANKER_SERVICE_URL", "http://localhost:8020")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:8030")
SERVICE_AUTH_MODE = os.getenv("SERVICE_AUTH_MODE", "none")
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")
RERANK_QUALITY_THRESHOLD = float(os.getenv("RERANK_QUALITY_THRESHOLD", "0.30"))
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def cors_allow_origins() -> List[str]:
    if CORS_ALLOW_ORIGINS.strip() == "*":
        return ["*"]
    return [o.strip() for o in CORS_ALLOW_ORIGINS.split(",") if o.strip()]
