import type {
  AutoRouteQueryResponse,
  AutoRouteState,
  CompareResponse,
} from "@/types";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8080";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (body?.error) message = body.error;
    } catch {
      // response wasn't JSON — keep the generic message
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

/** Fans a question out to base_model, rag, and finetuned, then returns the
 * judge's side-by-side comparison. This is the "wow moment" call. */
export async function compareQuery(question: string): Promise<CompareResponse> {
  const res = await fetch(`${GATEWAY_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return handleResponse<CompareResponse>(res);
}

/** Sends a question straight to the currently-winning strategy, skipping the
 * judge call. Only works once auto-route mode is enabled. */
export async function autoRouteQuery(
  question: string
): Promise<AutoRouteQueryResponse> {
  const res = await fetch(`${GATEWAY_URL}/query/auto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return handleResponse<AutoRouteQueryResponse>(res);
}

export async function getAutoRouteState(): Promise<AutoRouteState> {
  const res = await fetch(`${GATEWAY_URL}/autoroute`, { cache: "no-store" });
  return handleResponse<AutoRouteState>(res);
}

export async function setAutoRouteEnabled(
  enabled: boolean
): Promise<AutoRouteState> {
  const res = await fetch(`${GATEWAY_URL}/autoroute/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  return handleResponse<AutoRouteState>(res);
}