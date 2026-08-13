package handlers

import (
	"context"

	"github.com/gofiber/fiber/v2"

	"github.com/MuaazTasawar/alloy/gateway/internal/db"
	"github.com/MuaazTasawar/alloy/gateway/internal/models"
)

func (h *Handler) insertQuery(ctx context.Context, question, mode string) (string, error) {
	return db.InsertQuery(ctx, h.DB, question, mode)
}

func (h *Handler) insertResponse(ctx context.Context, queryID string, resp models.StrategyResponse) (string, error) {
	return db.InsertResponse(ctx, h.DB, queryID, resp.Strategy, resp.Answer, resp.LatencyMs, resp.InputTokens, resp.OutputTokens, resp.CostUSD)
}

func (h *Handler) insertJudgeScore(ctx context.Context, responseID string, score float64, reasoning string) error {
	return db.InsertJudgeScore(ctx, h.DB, responseID, score, reasoning)
}

func (h *Handler) updateWinningStrategy(ctx context.Context, queryID, strategy string) error {
	return db.UpdateWinningStrategy(ctx, h.DB, queryID, strategy)
}

// GetAutoRouteState reports whether auto-route mode is on and which strategy
// is currently winning.
func (h *Handler) GetAutoRouteState(c *fiber.Ctx) error {
	ctx := c.Context()
	state, err := db.GetRoutingState(ctx, h.DB)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to read routing state"})
	}

	return c.JSON(models.AutoRouteStateResponse{
		AutoRouteEnabled: state.AutoRouteEnabled,
		ActiveStrategy:   state.ActiveStrategy.String,
	})
}

// ToggleAutoRoute flips auto-route mode on or off. Turning it on requires a
// winning strategy to already exist (i.e. at least one /query compare has run).
func (h *Handler) ToggleAutoRoute(c *fiber.Ctx) error {
	var req models.AutoRouteToggleRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}

	ctx := c.Context()
	state, err := db.GetRoutingState(ctx, h.DB)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to read routing state"})
	}

	if req.Enabled && !state.ActiveStrategy.Valid {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "no winning strategy yet — run a /query comparison first",
		})
	}

	if err := db.SetRoutingState(ctx, h.DB, state.ActiveStrategy.String, req.Enabled); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to update routing state"})
	}

	return c.JSON(models.AutoRouteStateResponse{
		AutoRouteEnabled: req.Enabled,
		ActiveStrategy:   state.ActiveStrategy.String,
	})
}

// AutoRouteQuery silently routes to whichever strategy last won, skipping the
// judge call entirely — this is what powers the "auto-route mode" toggle in
// the dashboard picking the winning strategy live for subsequent questions.
func (h *Handler) AutoRouteQuery(c *fiber.Ctx) error {
	var req models.QueryRequest
	if err := c.BodyParser(&req); err != nil || req.Question == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "question is required"})
	}

	ctx := c.Context()
	state, err := db.GetRoutingState(ctx, h.DB)
	if err != nil || !state.AutoRouteEnabled || !state.ActiveStrategy.Valid {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "auto-route is not enabled"})
	}

	strategy := state.ActiveStrategy.String

	var resp models.StrategyResponse
	switch strategy {
	case "base_model":
		resp, err = h.RAG.QueryBase(ctx, req.Question)
	case "rag":
		resp, err = h.RAG.QueryRAG(ctx, req.Question)
	case "finetuned":
		resp, err = h.Finetune.Query(ctx, req.Question)
	}
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(fiber.Map{"error": err.Error()})
	}

	queryID, dbErr := h.insertQuery(ctx, req.Question, "auto_route")
	if dbErr == nil {
		_, _ = h.insertResponse(ctx, queryID, resp)
		_ = h.updateWinningStrategy(ctx, queryID, strategy)
	}

	return c.JSON(models.AutoRouteQueryResponse{
		QueryID:  queryID,
		Question: req.Question,
		Strategy: strategy,
		Response: resp,
	})
}
