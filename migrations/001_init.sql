-- Phase 0: Core extensions and schema setup

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tracks the routing strategy an answer came from, used across
-- documents, queries, responses, and score tables.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strategy_type') THEN
        CREATE TYPE strategy_type AS ENUM ('base_model', 'rag', 'finetuned');
    END IF;
END$$;