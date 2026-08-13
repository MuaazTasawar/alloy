package handlers

import (
	"context"
	"sync"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MuaazTasawar/alloy/gateway/internal/clients"
	"github.com/MuaazTasawar/alloy/gateway/internal/models"
)

type Handler struct {
	RAG      *clients.RAGClient
	Finetune *clients.FinetuneClient
	Judge    *clients.JudgeClient
	DB       *pgxpool.Pool
}

func NewHandler(rag *clients.RAGClient, finetune *clients.FinetuneClient, judge *clients.JudgeClient, db *pgxpool.Pool) *Handler {
	return &Handler{RAG: rag, Finetune: finetune, Judge: judge, DB: db}
}

func (h *Handler) Health(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{"status": "ok", "service": "gateway"})
}

// fanOut runs all three strategies concurrently and returns them keyed by strategy name.
func (h *Handler) fanOut(ctx context.Context, question string) map[string]models.StrategyResponse {
	results := make(map[string]models.StrategyResponse, 3)
	var mu sync.Mutex
	var wg sync.WaitGroup

	run := func(strategy string, fn func() (models.StrategyResponse, error)) {
		defer wg.Done()
		resp, err := fn()
		if err != nil && resp.Error == "" {
			resp.Error = err.Error()
		}
		resp.Strategy = strategy
		mu.Lock()
		results[strategy] = resp
		mu.Unlock()
	}

	wg.Add(3)
	go run("base_model", func() (models.StrategyResponse, error) { return h.RAG.QueryBase(ctx, question) })
	go run("rag", func() (models.StrategyResponse, error) { return h.RAG.QueryRAG(ctx, question) })
	go run("finetuned", func() (models.StrategyResponse, error) { return h.Finetune.Query(ctx, question) })
	wg.Wait()

	return results
}

// CompareQuery is the "wow moment" endpoint: fan a question out to all three
// strategies, judge them head to head, persist everything, and return the
// side-by-side comparison.
func (h *Handler) CompareQuery(c *fiber.Ctx) error {
	var req models.QueryRequest
	if err := c.BodyParser(&req); err != nil || req.Question == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "question is required"})
	}

	ctx := c.Context()

	queryID, err := h.insertQuery(ctx, req.Question, "compare")
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to log query"})
	}

	results := h.fanOut(ctx, req.Question)

	compareResult, err := h.Judge.Compare(
		ctx,
		req.Question,
		results["base_model"].Answer,
		results["rag"].Answer,
		results["finetuned"].Answer,
	)

	responses := make([]models.StrategyResponse, 0, 3)
	for _, strategy := range []string{"base_model", "rag", "finetuned"} {
		resp := results[strategy]

		if err == nil {
			if detail, ok := compareResult.Scores[strategy]; ok {
				resp.Score = detail.Score
				resp.Reasoning = detail.Reasoning
			}
		}

		responseID, dbErr := h.insertResponse(ctx, queryID, resp)
		if dbErr == nil && err == nil {
			if detail, ok := compareResult.Scores[strategy]; ok {
				_ = h.insertJudgeScore(ctx, responseID, detail.Score, detail.Reasoning)
			}
		}

		responses = append(responses, resp)
	}

	winner := compareResult.Winner
	winnerReasoning := compareResult.WinnerReasoning
	if err == nil && winner != "" {
		_ = h.updateWinningStrategy(ctx, queryID, winner)
	}

	return c.JSON(models.CompareResponse{
		QueryID:         queryID,
		Question:        req.Question,
		Responses:       responses,
		Winner:          winner,
		WinnerReasoning: winnerReasoning,
	})
}
