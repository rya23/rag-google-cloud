# Decoupled RAG on Google Cloud (Learning Project)

A simple 4-layer Retrieval-Augmented Generation project designed to learn cloud deployment on GCP without heavy infrastructure complexity.

## Architecture (4 layers)

1. **Frontend (HTML + JS)**
   - Sends user query to the orchestrator.
   - Displays answer, sources, and retrieval path.

2. **Orchestrator (FastAPI + LangGraph)**
   - Controls RAG flow and fallback decisions.
   - Calls independent embedding and reranker services.
   - Queries PostgreSQL + pgvector.
   - Calls Groq LLM for final answer generation.

3. **Inference Layer (Decoupled Artifacts)**
   - **Embedding service**: Matryoshka embedding model, supports `128` and `768` dimensions.
   - **Reranker service**: Cross-encoder reranker.
   - Both are separate services so one can fail without crashing the other.

4. **Data Layer (PostgreSQL + pgvector)**
   - Stores chunks and metadata.
   - Stores both `embedding_128` and `embedding_768` in the same table.

## Why this design

- Simple enough to implement and deploy quickly on Cloud Run.
- Decoupled enough to discuss service boundaries in interviews.
- Uses a practical Matryoshka strategy:
  - **Fast path**: search with 128d vectors.
  - **Fallback path**: search with 768d vectors when retrieval quality is weak.

## Query flow

1. Frontend calls `POST /query` on orchestrator.
2. Orchestrator gets 128d query embedding from embedding service.
3. Orchestrator retrieves top-k from `embedding_128` in pgvector.
4. Orchestrator calls reranker service and checks quality threshold.
5. If quality is strong -> generate answer with Groq.
6. If quality is weak -> repeat retrieval with 768d vectors, rerank, then generate.
7. Return answer + sources + `path_used` (`fast_128` or `fallback_768`).

## Project structure

```text
.
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── orchestrator/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── embedding-service/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── reranker-service/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── data/
│   ├── init/
│   └── seed/
├── infra/
│   └── docker-compose.yml
└── .env.example
```

## Local quickstart

1. Create env file:

```bash
cp .env.example .env
```

2. Set your Groq key in `.env`:

```bash
GROQ_API_KEY=your_key_here
```

3. Start the stack:

```bash
docker compose -f infra/docker-compose.yml up --build
```

This project pins CPU-only PyTorch wheels in both inference services to avoid CUDA package downloads.

The embedding model and reranker model load lazily on first request to keep startup and health checks fast.

4. Seed data:

```bash
curl -X POST http://localhost:8000/seed
```

5. Generate embeddings for all sources:

```bash
curl -X POST http://localhost:8000/ingest/all
```

6. Open UI:

```text
http://localhost:3000
```

## Core APIs

- Orchestrator
  - `GET /health`
  - `POST /seed`
  - `POST /ingest/source`
  - `POST /ingest/all`
  - `POST /query`
- Embedding service
  - `GET /health`
  - `POST /embed`
- Reranker service
  - `GET /health`
  - `POST /rerank`

## Cloud Run deployment path (Path 1)

Use this managed setup for interview-friendly delivery:

- Deploy `frontend`, `orchestrator`, `embedding-service`, and `reranker-service` as separate Cloud Run services.
- Use Cloud SQL PostgreSQL with `pgvector` enabled.
- Store `GROQ_API_KEY` and DB credentials in Secret Manager.
- Configure service-to-service URLs via environment variables.

This gives a strong “ship fast with managed services” story while keeping clean service boundaries.

## Interview talking points

- I separated embedding and reranking into independent artifacts for fault isolation and independent scaling.
- I used a Matryoshka two-dimension strategy (128/768) to balance latency vs retrieval quality.
- I chose Cloud Run + Cloud SQL first to reduce ops overhead and focus on system design and model behavior.
- I can later move inference services to GPU or GKE if traffic/model load grows.
