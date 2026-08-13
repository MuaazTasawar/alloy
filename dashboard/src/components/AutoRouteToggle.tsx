"use client";

import type { AutoRouteState } from "@/types";

interface AutoRouteToggleProps {
  state: AutoRouteState | null;
  onToggle: (enabled: boolean) => void;
  isBusy: boolean;
  hasWinner: boolean;
}

const STRATEGY_LABELS: Record<string, string> = {
  base_model: "Base Model",
  rag: "RAG",
  finetuned: "Fine-Tuned LoRA",
};

export default function AutoRouteToggle({
  state,
  onToggle,
  isBusy,
  hasWinner,
}: AutoRouteToggleProps) {
  const enabled = state?.auto_route_enabled ?? false;
  const activeStrategy = state?.active_strategy;

  return (
    <div className="flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-900 p-4">
      <div>
        <p className="text-sm font-semibold text-neutral-200">Auto-Route Mode</p>
        <p className="text-xs text-neutral-500">
          {enabled && activeStrategy
            ? `Silently routing every question to ${STRATEGY_LABELS[activeStrategy] || activeStrategy}`
            : hasWinner
            ? "A winning strategy is available — flip on to auto-route live"
            : "Run a comparison first to establish a winning strategy"}
        </p>
      </div>

      <button
        onClick={() => onToggle(!enabled)}
        disabled={isBusy || (!enabled && !hasWinner)}
        role="switch"
        aria-checked={enabled}
        className={`relative h-7 w-12 shrink-0 rounded-full transition disabled:cursor-not-allowed disabled:opacity-40 ${
          enabled ? "bg-emerald-600" : "bg-neutral-700"
        }`}
      >
        <span
          className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-transform ${
            enabled ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}