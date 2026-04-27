import os


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5432/ragdb")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8010")
SERVICE_AUTH_MODE = os.getenv("SERVICE_AUTH_MODE", "none")

INGEST_UPLOAD_DIR = os.getenv("INGEST_UPLOAD_DIR", "/app/uploads")
INGEST_MAX_FILE_MB = int(os.getenv("INGEST_MAX_FILE_MB", "10"))
INGEST_CHUNK_SIZE = int(os.getenv("INGEST_CHUNK_SIZE", "800"))
INGEST_CHUNK_OVERLAP = int(os.getenv("INGEST_CHUNK_OVERLAP", "120"))
INGEST_BATCH_SIZE = int(os.getenv("INGEST_BATCH_SIZE", "16"))
INGEST_MAX_ATTEMPTS = int(os.getenv("INGEST_MAX_ATTEMPTS", "3"))

# GCS uploads bucket name (used to store uploaded files)
GCS_BUCKET = os.getenv("GCS_BUCKET", "matryoshka-search-uploads")

# Pub/Sub event-driven configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
PUBSUB_TOPIC_NAME = os.getenv("PUBSUB_TOPIC_NAME", "ingestion-jobs")
PUBSUB_SUBSCRIPTION_NAME = os.getenv("PUBSUB_SUBSCRIPTION_NAME", "ingestion-jobs-sub")
