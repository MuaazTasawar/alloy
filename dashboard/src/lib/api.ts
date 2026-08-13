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

/** Wraps fetch with a timeout so a hung upstream service (e.g. a model still
 * loading on first request) fails fast with a readable error instead of
 * spinning the "Running..." button forever. */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(
        `Request timed out after ${timeoutMs / 1000}s — the gateway or an upstream service may be unavailable`
      );
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

// A full compare fans out to 3 model backends + a judge call, which can
// legitimately take a while on CPU-only local inference.
const COMPARE_TIMEOUT_MS = 90_000;
const DEFAULT_TIMEOUT_MS = 15_000;

/** Fans a question out to base_model, rag, and finetuned, then returns the
 * judge's side-by-side comparison. This is the "wow moment" call. */
export async function compareQuery(question: string): Promise<CompareResponse> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/query`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
    COMPARE_TIMEOUT_MS
  );
  return handleResponse<CompareResponse>(res);
}

/** Sends a question straight to the currently-winning strategy, skipping the
 * judge call. Only works once auto-route mode is enabled. */
export async function autoRouteQuery(
  question: string
): Promise<AutoRouteQueryResponse> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/query/auto`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
    COMPARE_TIMEOUT_MS
  );
  return handleResponse<AutoRouteQueryResponse>(res);
}

export async function getAutoRouteState(): Promise<AutoRouteState> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/autoroute`,
    { cache: "no-store" },
    DEFAULT_TIMEOUT_MS
  );
  return handleResponse<AutoRouteState>(res);
}

export async function setAutoRouteEnabled(
  enabled: boolean
): Promise<AutoRouteState> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/autoroute/toggle`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    },
    DEFAULT_TIMEOUT_MS
  );
  return handleResponse<AutoRouteState>(res);
}