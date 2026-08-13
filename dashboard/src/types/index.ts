export type Strategy = "base_model" | "rag" | "finetuned";

export interface StrategyResponse {
  strategy: Strategy;
  answer: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  score?: number;
  reasoning?: string;
  error?: string;
}

export interface CompareResponse {
  query_id: string;
  question: string;
  responses: StrategyResponse[];
  winner: Strategy | "";
  winner_reasoning: string;
}

export interface AutoRouteState {
  auto_route_enabled: boolean;
  active_strategy: Strategy | "";
}

export interface AutoRouteQueryResponse {
  query_id: string;
  question: string;
  strategy: Strategy;
  response: StrategyResponse;
}

export interface ApiError {
  error: string;
}