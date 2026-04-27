from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage

from app import config
from app.db import create_job, get_job, list_recent_jobs


ALLOWED_EXTENSIONS = {".txt", ".md"}


class JobStatus(BaseModel):
    id: int
    filename: str
    storage_path: str
    status: str
    error: str | None = None
    attempts: int


class JobListItem(BaseModel):
    id: int
    filename: str
    status: str
    error: str | None = None
    attempts: int


class JobCreateResponse(BaseModel):
    job_id: int
    status: str


class JobListResponse(BaseModel):
    jobs: List[JobListItem]


app = FastAPI(title="ingestion-service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Path(config.INGEST_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def upload_to_gcs(file_bytes: bytes, filename: str, bucket_name: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"uploads/{filename}")
    blob.upload_from_string(file_bytes)
    return f"gs://{bucket_name}/uploads/{filename}"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ingestion"}


@app.post("/ingest/file", response_model=JobCreateResponse)
async def ingest_file(file: UploadFile = File(...)) -> JobCreateResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename_required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="only_txt_md_supported")

    raw = await file.read()
    max_size = config.INGEST_MAX_FILE_MB * 1024 * 1024
    if len(raw) > max_size:
        raise HTTPException(status_code=400, detail="file_too_large")

    safe_name = file.filename.replace("/", "_").replace("..", "_")
    # upload file bytes to GCS and store the gs:// URI in the job
    storage_path = upload_to_gcs(raw, safe_name, config.GCS_BUCKET)

    job_id = create_job(filename=safe_name, storage_path=storage_path)
    return JobCreateResponse(job_id=job_id, status="pending")


@app.get("/ingest/jobs/{job_id}", response_model=JobStatus)
def ingest_job_status(job_id: int) -> JobStatus:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return JobStatus(
        id=job["id"],
        filename=job["filename"],
        storage_path=job["storage_path"],
        status=job["status"],
        error=job["error"],
        attempts=job["attempts"],
    )


@app.get("/ingest/jobs", response_model=JobListResponse)
def ingest_jobs() -> JobListResponse:
    jobs = list_recent_jobs(20)
    return JobListResponse(
        jobs=[
            JobListItem(
                id=j["id"],
                filename=j["filename"],
                status=j["status"],
                error=j["error"],
                attempts=j["attempts"],
            )
            for j in jobs
        ]
    )
