-- Phase 0: Live query logging, per-strategy responses, and judge scores

CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'compare', -- 'compare' (fan-out to all 3) or 'auto_route'
    winning_strategy strategy_type,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    strategy strategy_type NOT NULL,
    answer TEXT NOT NULL,
    latency_ms INT NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_responses_query_id ON responses(query_id);

CREATE TABLE IF NOT EXISTS judge_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    response_id UUID NOT NULL REFERENCES responses(id) ON DELETE CASCADE,
    score NUMERIC(3, 1) NOT NULL CHECK (score >= 0 AND score <= 10),
    reasoning TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_judge_scores_response_id ON judge_scores(response_id);

-- Auto-route mode: tracks which strategy is currently "winning" so the
-- gateway can silently route to it without a full fan-out + judge call.
CREATE TABLE IF NOT EXISTS routing_state (
    id INT PRIMARY KEY DEFAULT 1,
    active_strategy strategy_type,
    auto_route_enabled BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO routing_state (id, active_strategy, auto_route_enabled)
VALUES (1, NULL, false)
ON CONFLICT (id) DO NOTHING;