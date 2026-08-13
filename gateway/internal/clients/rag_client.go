package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/MuaazTasawar/alloy/gateway/internal/models"
)

type RAGClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewRAGClient(baseURL string) *RAGClient {
	return &RAGClient{
		baseURL:    baseURL,
		httpClient: &http.Client{Timeout: 60 * time.Second},
	}
}

type ragQueryPayload struct {
	Answer       string   `json:"answer"`
	LatencyMs    int      `json:"latency_ms"`
	InputTokens  int      `json:"input_tokens"`
	OutputTokens int      `json:"output_tokens"`
	CostUSD      float64  `json:"cost_usd"`
	Sources      []string `json:"sources"`
}

type basePayload struct {
	Answer       string  `json:"answer"`
	LatencyMs    int     `json:"latency_ms"`
	InputTokens  int     `json:"input_tokens"`
	OutputTokens int     `json:"output_tokens"`
	CostUSD      float64 `json:"cost_usd"`
}

func (c *RAGClient) post(ctx context.Context, path string, question string, out any) error {
	body, err := json.Marshal(map[string]string{"question": question})
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+path, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("rag-service %s returned status %d", path, resp.StatusCode)
	}

	return json.NewDecoder(resp.Body).Decode(out)
}

// QueryRAG calls the retrieval-augmented generation endpoint.
func (c *RAGClient) QueryRAG(ctx context.Context, question string) (models.StrategyResponse, error) {
	var payload ragQueryPayload
	if err := c.post(ctx, "/query", question, &payload); err != nil {
		return models.StrategyResponse{Strategy: "rag", Error: err.Error()}, err
	}

	return models.StrategyResponse{
		Strategy:     "rag",
		Answer:       payload.Answer,
		LatencyMs:    payload.LatencyMs,
		InputTokens:  payload.InputTokens,
		OutputTokens: payload.OutputTokens,
		CostUSD:      payload.CostUSD,
	}, nil
}

// QueryBase calls the plain base-model endpoint (no retrieval, no fine-tuning).
func (c *RAGClient) QueryBase(ctx context.Context, question string) (models.StrategyResponse, error) {
	var payload basePayload
	if err := c.post(ctx, "/base-query", question, &payload); err != nil {
		return models.StrategyResponse{Strategy: "base_model", Error: err.Error()}, err
	}

	return models.StrategyResponse{
		Strategy:     "base_model",
		Answer:       payload.Answer,
		LatencyMs:    payload.LatencyMs,
		InputTokens:  payload.InputTokens,
		OutputTokens: payload.OutputTokens,
		CostUSD:      payload.CostUSD,
	}, nil
}
