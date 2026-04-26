CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding_128 VECTOR(128),
    embedding_768 VECTOR(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS documents_embedding_128_ivfflat
    ON documents USING ivfflat (embedding_128 vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS documents_embedding_768_ivfflat
    ON documents USING ivfflat (embedding_768 vector_cosine_ops)
    WITH (lists = 100);
