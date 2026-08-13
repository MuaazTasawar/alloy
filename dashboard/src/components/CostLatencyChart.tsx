"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { StrategyResponse } from "@/types";

const STRATEGY_LABELS: Record<string, string> = {
  base_model: "Base Model",
  rag: "RAG",
  finetuned: "Fine-Tuned",
};

interface CostLatencyChartProps {
  responses: StrategyResponse[];
}

export default function CostLatencyChart({ responses }: CostLatencyChartProps) {
  const data = responses.map((r) => ({
    name: STRATEGY_LABELS[r.strategy] || r.strategy,
    "Latency (ms)": r.latency_ms,
    "Cost (¢)": Math.round(r.cost_usd * 100 * 100) / 100,
  }));

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-4">
      <h3 className="mb-4 text-sm font-semibold text-neutral-200">
        Latency &amp; Cost Comparison
      </h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
            <XAxis dataKey="name" stroke="#737373" fontSize={12} />
            <YAxis stroke="#737373" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#171717",
                border: "1px solid #404040",
                borderRadius: "0.5rem",
                fontSize: "12px",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
            <Bar dataKey="Latency (ms)" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Cost (¢)" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}