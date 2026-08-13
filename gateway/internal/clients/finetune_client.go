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

type FinetuneClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewFinetuneClient(baseURL string) *FinetuneClient {
	return &FinetuneClient{
		baseURL:    baseURL,
		httpClient: &http.Client{Timeout: 60 * time.Second},
	}
}

type finetunePayload struct {
	Answer       string  `json:"answer"`
	LatencyMs    int     `json:"latency_ms"`
	InputTokens  int     `json:"input_tokens"`
	OutputTokens int     `json:"output_tokens"`
	CostUSD      float64 `json:"cost_usd"`
}

func (c *FinetuneClient) Query(ctx context.Context, question string) (models.StrategyResponse, error) {
	body, err := json.Marshal(map[string]string{"question": question})
	if err != nil {
		return models.StrategyResponse{Strategy: "finetuned", Error: err.Error()}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/query", bytes.NewReader(body))
	if err != nil {
		return models.StrategyResponse{Strategy: "finetuned", Error: err.Error()}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return models.StrategyResponse{Strategy: "finetuned", Error: err.Error()}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		err := fmt.Errorf("finetune-service /query returned status %d", resp.StatusCode)
		return models.StrategyResponse{Strategy: "finetuned", Error: err.Error()}, err
	}

	var payload finetunePayload
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return models.StrategyResponse{Strategy: "finetuned", Error: err.Error()}, err
	}

	return models.StrategyResponse{
		Strategy:     "finetuned",
		Answer:       payload.Answer,
		LatencyMs:    payload.LatencyMs,
		InputTokens:  payload.InputTokens,
		OutputTokens: payload.OutputTokens,
		CostUSD:      payload.CostUSD,
	}, nil
}
