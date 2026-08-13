package main

import (
	"context"
	"log"

	"github.com/MuaazTasawar/alloy/gateway/internal/clients"
	"github.com/MuaazTasawar/alloy/gateway/internal/config"
	"github.com/MuaazTasawar/alloy/gateway/internal/db"
	"github.com/MuaazTasawar/alloy/gateway/internal/handlers"
	"github.com/MuaazTasawar/alloy/gateway/internal/router"
)

func main() {
	cfg := config.Load()

	ctx := context.Background()
	pool, err := db.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("failed to connect to database: %v", err)
	}
	defer pool.Close()

	ragClient := clients.NewRAGClient(cfg.RAGServiceURL)
	finetuneClient := clients.NewFinetuneClient(cfg.FinetuneServiceURL)
	judgeClient := clients.NewJudgeClient(cfg.JudgeServiceURL)

	h := handlers.NewHandler(ragClient, finetuneClient, judgeClient, pool)
	app := router.New(h)

	log.Printf("alloy gateway listening on :%s", cfg.Port)
	if err := app.Listen(":" + cfg.Port); err != nil {
		log.Fatalf("gateway crashed: %v", err)
	}
}
