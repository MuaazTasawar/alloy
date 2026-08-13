package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/MuaazTasawar/alloy/gateway/internal/clients"
	"github.com/MuaazTasawar/alloy/gateway/internal/config"
	"github.com/MuaazTasawar/alloy/gateway/internal/db"
	"github.com/MuaazTasawar/alloy/gateway/internal/handlers"
	"github.com/MuaazTasawar/alloy/gateway/internal/router"
)

func main() {
	cfg := config.Load()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := db.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("failed to connect to database: %v", err)
	}
	defer pool.Close()

	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("database did not respond to ping: %v", err)
	}

	ragClient := clients.NewRAGClient(cfg.RAGServiceURL)
	finetuneClient := clients.NewFinetuneClient(cfg.FinetuneServiceURL)
	judgeClient := clients.NewJudgeClient(cfg.JudgeServiceURL)

	h := handlers.NewHandler(ragClient, finetuneClient, judgeClient, pool)
	app := router.New(h)

	// Run the server in a goroutine so the main goroutine can wait on an OS
	// signal and shut down cleanly instead of dropping in-flight requests.
	go func() {
		log.Printf("alloy gateway listening on :%s", cfg.Port)
		if err := app.Listen(":" + cfg.Port); err != nil {
			log.Fatalf("gateway crashed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("shutdown signal received, draining in-flight requests...")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer shutdownCancel()

	if err := app.ShutdownWithContext(shutdownCtx); err != nil {
		log.Printf("forced shutdown: %v", err)
	}
	log.Println("gateway stopped cleanly")
}
