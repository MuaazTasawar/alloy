import type { StrategyResponse } from "@/types";

const STRATEGY_LABELS: Record<string, string> = {
  base_model: "Base Model",
  rag: "RAG",
  finetuned: "Fine-Tuned LoRA",
};

const STRATEGY_COLORS: Record<string, string> = {
  base_model: "border-neutral-700",
  rag: "border-sky-700",
  finetuned: "border-violet-700",
};

interface ResponseCardProps {
  response: StrategyResponse;
  isWinner: boolean;
}

export default function ResponseCard({ response, isWinner }: ResponseCardProps) {
  const borderClass = isWinner
    ? "border-emerald-500 shadow-lg shadow-emerald-500/10"
    : STRATEGY_COLORS[response.strategy] || "border-neutral-700";

  return (
    <div
      className={`flex flex-col rounded-xl border-2 bg-neutral-900 p-4 transition ${borderClass}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-200">
          {STRATEGY_LABELS[response.strategy] || response.strategy}
        </h3>
        {isWinner && (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-400">
            Winner
          </span>
        )}
      </div>

      {response.error ? (
        <p className="text-sm text-red-400">Error: {response.error}</p>
      ) : (
        <p className="mb-4 flex-1 whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
          {response.answer}
        </p>
      )}

      <div className="mt-auto grid grid-cols-2 gap-2 border-t border-neutral-800 pt-3 text-xs text-neutral-500">
        <span>Latency: {response.latency_ms} ms</span>
        <span>
          Cost: {response.cost_usd > 0 ? `$${response.cost_usd.toFixed(4)}` : "Free"}
        </span>
        <span>
          Tokens: {response.input_tokens} in / {response.output_tokens} out
        </span>
        {typeof response.score === "number" && (
          <span className="font-medium text-neutral-300">
            Score: {response.score.toFixed(1)}/10
          </span>
        )}
      </div>

      {response.reasoning && (
        <p className="mt-2 border-t border-neutral-800 pt-2 text-xs italic text-neutral-500">
          {response.reasoning}
        </p>
      )}
    </div>
  );
}