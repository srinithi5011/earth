-- Darukaa Earth — PostgreSQL + pgvector schema
-- Applied automatically by the `postgres` service in docker-compose.yml
-- (mounted into /docker-entrypoint-initdb.d/). This mirrors the
-- SQLAlchemy models in backend/app/models/*.py; the app itself creates
-- tables via SQLAlchemy on startup for both SQLite and Postgres, but this
-- file additionally sets up the pgvector extension and a native vector
-- column + ANN index for knowledge_chunks, which SQLAlchemy's
-- database-agnostic JSON column cannot express.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- NOTE: backend/app/models/database.py::init_db() will create every
-- table via Base.metadata.create_all(). This script runs BEFORE the app
-- starts (via docker-entrypoint-initdb.d) and only needs to prepare the
-- extension + the one Postgres-native column SQLAlchemy can't express.
-- If you are provisioning Postgres manually (outside docker-compose),
-- run this file, then run `python -c "from app.models.database import init_db; init_db()"`
-- from backend/, then run the block below to upgrade the embedding
-- column to a native vector type.

-- Run this AFTER the app has created tables once (safe to re-run):
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_chunks'
    ) THEN
        BEGIN
            ALTER TABLE knowledge_chunks
                ALTER COLUMN embedding TYPE vector(4096)
                USING NULL; -- existing JSON embeddings are re-generated via reindex_all_embeddings()
        EXCEPTION WHEN OTHERS THEN
            -- Column may already be vector type, or table may not exist yet on first run; ignore.
            NULL;
        END;

        BEGIN
            CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
                ON knowledge_chunks
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
END $$;

-- Helpful metadata indexes (safe no-ops if already present)
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_topic ON knowledge_chunks (topic);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_region ON knowledge_chunks (region);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id ON knowledge_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_env_relationships_source ON environmental_relationships (source_metric);
CREATE INDEX IF NOT EXISTS idx_env_relationships_target ON environmental_relationships (target_metric);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations (session_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id);
