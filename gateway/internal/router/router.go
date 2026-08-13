package router

import (
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"

	"github.com/MuaazTasawar/alloy/gateway/internal/handlers"
)

func New(h *handlers.Handler) *fiber.App {
	app := fiber.New()

	app.Use(cors.New())

	app.Get("/health", h.Health)

	app.Post("/query", h.CompareQuery)
	app.Post("/query/auto", h.AutoRouteQuery)

	app.Get("/autoroute", h.GetAutoRouteState)
	app.Post("/autoroute/toggle", h.ToggleAutoRoute)

	return app
}
