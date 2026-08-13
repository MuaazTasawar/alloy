package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type JudgeClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewJudgeClient(baseURL string) *JudgeClient {
	return &JudgeClient{
		baseURL:    baseURL,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

type ScoreDetail struct {
	Score     float64 `json:"score"`
	Reasoning string  `json:"reasoning"`
}

type CompareResult struct {
	Scores          map[string]ScoreDetail `json:"scores"`
	Winner          string                 `json:"winner"`
	WinnerReasoning string                 `json:"winner_reasoning"`
}

// Compare sends all three strategies' answers to the judge in a single call so
// the winner determination is consistent, rather than three isolated scores.
func (c *JudgeClient) Compare(ctx context.Context, question, baseAnswer, ragAnswer, finetunedAnswer string) (CompareResult, error) {
	body, err := json.Marshal(map[string]string{
		"question":          question,
		"base_model_answer": baseAnswer,
		"rag_answer":        ragAnswer,
		"finetuned_answer":  finetunedAnswer,
	})
	if err != nil {
		return CompareResult{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/compare", bytes.NewReader(body))
	if err != nil {
		return CompareResult{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return CompareResult{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return CompareResult{}, fmt.Errorf("judge-service /compare returned status %d", resp.StatusCode)
	}

	var result CompareResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return CompareResult{}, err
	}
	return result, nil
}
