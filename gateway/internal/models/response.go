package models

// StrategyResponse is a single strategy's answer to a question, normalized
// across the base model, RAG, and fine-tuned services.
type StrategyResponse struct {
	Strategy     string  `json:"strategy"`
	Answer       string  `json:"answer"`
	LatencyMs    int     `json:"latency_ms"`
	InputTokens  int     `json:"input_tokens"`
	OutputTokens int     `json:"output_tokens"`
	CostUSD      float64 `json:"cost_usd"`
	Score        float64 `json:"score,omitempty"`
	Reasoning    string  `json:"reasoning,omitempty"`
	Error        string  `json:"error,omitempty"`
}

// CompareResponse is the "wow moment" payload: all three strategies side by
// side, plus the judge's verdict on which one won and why.
type CompareResponse struct {
	QueryID         string             `json:"query_id"`
	Question        string             `json:"question"`
	Responses       []StrategyResponse `json:"responses"`
	Winner          string             `json:"winner"`
	WinnerReasoning string             `json:"winner_reasoning"`
}

type QueryRequest struct {
	Question string `json:"question"`
}

type AutoRouteToggleRequest struct {
	Enabled bool `json:"enabled"`
}

type AutoRouteStateResponse struct {
	AutoRouteEnabled bool   `json:"auto_route_enabled"`
	ActiveStrategy   string `json:"active_strategy"`
}

type AutoRouteQueryResponse struct {
	QueryID  string           `json:"query_id"`
	Question string           `json:"question"`
	Strategy string           `json:"strategy"`
	Response StrategyResponse `json:"response"`
}
