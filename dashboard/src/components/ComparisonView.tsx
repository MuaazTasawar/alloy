import type { CompareResponse } from "@/types";
import CostLatencyChart from "./CostLatencyChart";
import ResponseCard from "./ResponseCard";

interface ComparisonViewProps {
  result: CompareResponse;
}

export default function ComparisonView({ result }: ComparisonViewProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-neutral-500">
          Question
        </p>
        <p className="mt-1 text-base text-neutral-200">{result.question}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {result.responses.map((response) => (
          <ResponseCard
            key={response.strategy}
            response={response}
            isWinner={response.strategy === result.winner}
          />
        ))}
      </div>

      {result.winner_reasoning && (
        <div className="rounded-xl border border-emerald-800 bg-emerald-500/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-400">
            Why {result.winner.replace("_", " ")} won
          </p>
          <p className="mt-1 text-sm text-neutral-300">
            {result.winner_reasoning}
          </p>
        </div>
      )}

      <CostLatencyChart responses={result.responses} />
    </div>
  );
}