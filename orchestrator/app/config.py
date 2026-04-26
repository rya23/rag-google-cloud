import os


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5432/ragdb")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8010")
RERANKER_SERVICE_URL = os.getenv("RERANKER_SERVICE_URL", "http://localhost:8020")
RERANK_QUALITY_THRESHOLD = float(os.getenv("RERANK_QUALITY_THRESHOLD", "0.30"))
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
