CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    attempts INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS filename TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS job_id BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_index INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_documents_ingestion_job'
    ) THEN
        ALTER TABLE documents
            ADD CONSTRAINT fk_documents_ingestion_job
            FOREIGN KEY (job_id) REFERENCES ingestion_jobs(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ingestion_jobs_status_idx
    ON ingestion_jobs (status, id);

CREATE INDEX IF NOT EXISTS documents_source_chunk_idx
    ON documents (source, chunk_index);
