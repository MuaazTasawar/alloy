package config

import "os"

type Config struct {
	Port               string
	DatabaseURL        string
	RAGServiceURL      string
	FinetuneServiceURL string
	JudgeServiceURL    string
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func Load() *Config {
	return &Config{
		Port:               getEnv("GATEWAY_PORT", "8080"),
		DatabaseURL:        getEnv("DATABASE_URL", "postgres://alloy:alloy_dev_password@postgres:5432/alloy?sslmode=disable"),
		RAGServiceURL:      getEnv("RAG_SERVICE_URL", "http://rag-service:8001"),
		FinetuneServiceURL: getEnv("FINETUNE_SERVICE_URL", "http://finetune-service:8002"),
		JudgeServiceURL:    getEnv("JUDGE_SERVICE_URL", "http://judge-service:8003"),
	}
}
