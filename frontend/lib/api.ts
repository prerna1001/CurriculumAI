import type {
  ErrorBody,
  PublishResponse,
  SearchResponse,
  SelectResponse,
} from "./types";

/**
 * The FastAPI backend origin. Override in frontend/.env.local if it runs
 * elsewhere. Deterministic demo data comes from the backend's own
 * CURRICULUMAI_MODE=fixture, not from the frontend.
 */
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly retryable: boolean,
  ) {
    super(message);
  }
}

function endpoint(name: "search" | "select" | "publish"): string {
  return `${BASE}/api/${name}`;
}

async function post<T>(name: "search" | "select" | "publish", body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(endpoint(name), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("network", "Could not reach the backend. Is it running?", true);
  }

  const text = await response.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError("bad_response", `Backend returned non-JSON (${response.status}).`, true);
  }

  if (!response.ok) {
    const body = parsed as ErrorBody | null;
    if (body?.error) {
      throw new ApiError(body.error.code, body.error.message, body.error.retryable);
    }
    throw new ApiError("unknown", `Request failed (${response.status}).`, true);
  }

  return parsed as T;
}

export const search = (subject: string, level: string) =>
  post<SearchResponse>("search", { subject, level });

export const select = (sessionId: string, cardIds: string[]) =>
  post<SelectResponse>("select", { session_id: sessionId, card_ids: cardIds });

export const publish = (selectionId: string) =>
  post<PublishResponse>("publish", { selection_id: selectionId });
