package router

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"

	"github.com/MuaazTasawar/alloy/gateway/internal/handlers"
)

func New(h *handlers.Handler) *fiber.App {
	app := fiber.New(fiber.Config{
		// A fan-out to base_model + rag + finetuned, plus a judge call, can
		// legitimately take a while on CPU-only local inference — give it room
		// instead of the Fiber default.
		ReadTimeout:  90 * time.Second,
		WriteTimeout: 90 * time.Second,
		ErrorHandler: globalErrorHandler,
	})

	// recover() must be the outermost middleware so a panic in any handler
	// (e.g. a nil pointer from a malformed upstream response) returns a 500
	// instead of crashing the whole gateway process.
	app.Use(recover.New())
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} ${method} ${path} (${latency})\n",
	}))
	app.Use(cors.New())

	app.Get("/health", h.Health)

	app.Post("/query", h.CompareQuery)
	app.Post("/query/auto", h.AutoRouteQuery)

	app.Get("/autoroute", h.GetAutoRouteState)
	app.Post("/autoroute/toggle", h.ToggleAutoRoute)

	return app
}

// globalErrorHandler ensures every unhandled error returns a consistent JSON
// shape instead of Fiber's default plaintext response.
func globalErrorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}
	return c.Status(code).JSON(fiber.Map{"error": err.Error()})
}
