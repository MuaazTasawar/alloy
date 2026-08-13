"use client";

import { useEffect, useState } from "react";

import AutoRouteToggle from "@/components/AutoRouteToggle";
import ComparisonView from "@/components/ComparisonView";
import QueryInput from "@/components/QueryInput";
import ResponseCard from "@/components/ResponseCard";
import {
  autoRouteQuery,
  compareQuery,
  getAutoRouteState,
  setAutoRouteEnabled,
} from "@/lib/api";
import type {
  AutoRouteQueryResponse,
  AutoRouteState,
  CompareResponse,
} from "@/types";

export default function DashboardPage() {
  const [autoRoute, setAutoRoute] = useState<AutoRouteState | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(
    null
  );
  const [autoResult, setAutoResult] = useState<AutoRouteQueryResponse | null>(
    null
  );
  const [isQuerying, setIsQuerying] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refreshAutoRouteState();
  }, []);

  async function refreshAutoRouteState() {
    try {
      const state = await getAutoRouteState();
      setAutoRoute(state);
    } catch {
      // Gateway may not be up yet on first load — silently retry on next action.
    }
  }

  async function handleAsk(question: string) {
    setError(null);
    setIsQuerying(true);
    setAutoResult(null);

    try {
      if (autoRoute?.auto_route_enabled) {
        const result = await autoRouteQuery(question);
        setAutoResult(result);
      } else {
        const result = await compareQuery(question);
        setCompareResult(result);
        await refreshAutoRouteState();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsQuerying(false);
    }
  }

  async function handleToggle(enabled: boolean) {
    setError(null);
    setIsToggling(true);
    try {
      const state = await setAutoRouteEnabled(enabled);
      setAutoRoute(state);
      if (!enabled) setAutoResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle auto-route");
    } finally {
      setIsToggling(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12">
      <header>
        <h1 className="text-2xl font-bold text-neutral-100">Alloy</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Ask one question. Watch base model, RAG, and a fine-tuned LoRA model
          answer side by side — then let the winner take over.
        </p>
      </header>

      <AutoRouteToggle
        state={autoRoute}
        onToggle={handleToggle}
        isBusy={isToggling}
        hasWinner={Boolean(compareResult?.winner)}
      />

      <QueryInput
        onSubmit={handleAsk}
        isLoading={isQuerying}
        placeholder={
          autoRoute?.auto_route_enabled
            ? "Auto-route is on — this goes straight to the winning strategy"
            : "Ask a question about your corpus..."
        }
      />

      {error && (
        <div className="rounded-lg border border-red-900 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {autoResult && (
        <div className="flex flex-col gap-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            Auto-routed answer
          </p>
          <ResponseCard response={autoResult.response} isWinner />
        </div>
      )}

      {!autoResult && compareResult && (
        <ComparisonView result={compareResult} />
      )}

      {!compareResult && !autoResult && !isQuerying && (
        <div className="rounded-xl border border-dashed border-neutral-800 p-10 text-center text-sm text-neutral-500">
          Ask a question above to see base model, RAG, and fine-tuned answers
          compared side by side.
        </div>
      )}
    </main>
  );
}