CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.chunks (
    chunk_id       bigserial PRIMARY KEY,
    doc_id         text NOT NULL,
    doc_title      text NOT NULL,
    source_path    text NOT NULL,
    content_type   text NOT NULL,          -- paragraph | table | slide
    section        text,
    chunk_index    int  NOT NULL,
    content        text NOT NULL,          -- header + text
    allowed_groups text[] NOT NULL DEFAULT '{all}',
    embedding      vector(1536),
    tsv            tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    UNIQUE (doc_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);
GRANT SELECT ON chunks TO chatbot_ro;
