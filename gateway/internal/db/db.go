package db

import (
	"context"
	"database/sql"

	"github.com/jackc/pgx/v5/pgxpool"
)

func NewPool(ctx context.Context, databaseURL string) (*pgxpool.Pool, error) {
	return pgxpool.New(ctx, databaseURL)
}

func InsertQuery(ctx context.Context, pool *pgxpool.Pool, question, mode string) (string, error) {
	var queryID string
	err := pool.QueryRow(ctx,
		`INSERT INTO queries (question, mode) VALUES ($1, $2) RETURNING id`,
		question, mode,
	).Scan(&queryID)
	return queryID, err
}

func UpdateWinningStrategy(ctx context.Context, pool *pgxpool.Pool, queryID, strategy string) error {
	_, err := pool.Exec(ctx,
		`UPDATE queries SET winning_strategy = $1 WHERE id = $2`,
		strategy, queryID,
	)
	return err
}

func InsertResponse(ctx context.Context, pool *pgxpool.Pool, queryID, strategy, answer string, latencyMs, inputTokens, outputTokens int, costUSD float64) (string, error) {
	var responseID string
	err := pool.QueryRow(ctx,
		`INSERT INTO responses (query_id, strategy, answer, latency_ms, input_tokens, output_tokens, cost_usd)
		 VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id`,
		queryID, strategy, answer, latencyMs, inputTokens, outputTokens, costUSD,
	).Scan(&responseID)
	return responseID, err
}

func InsertJudgeScore(ctx context.Context, pool *pgxpool.Pool, responseID string, score float64, reasoning string) error {
	_, err := pool.Exec(ctx,
		`INSERT INTO judge_scores (response_id, score, reasoning) VALUES ($1, $2, $3)`,
		responseID, score, reasoning,
	)
	return err
}

type RoutingState struct {
	ActiveStrategy   sql.NullString
	AutoRouteEnabled bool
}

func GetRoutingState(ctx context.Context, pool *pgxpool.Pool) (RoutingState, error) {
	var state RoutingState
	err := pool.QueryRow(ctx,
		`SELECT active_strategy, auto_route_enabled FROM routing_state WHERE id = 1`,
	).Scan(&state.ActiveStrategy, &state.AutoRouteEnabled)
	return state, err
}

func SetRoutingState(ctx context.Context, pool *pgxpool.Pool, strategy string, enabled bool) error {
	_, err := pool.Exec(ctx,
		`UPDATE routing_state SET active_strategy = $1, auto_route_enabled = $2, updated_at = now() WHERE id = 1`,
		strategy, enabled,
	)
	return err
}
