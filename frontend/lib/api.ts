import {
  HealthResponse,
  QueryRequest,
  QueryResponse,
} from "@/types/compliance";
import { DEMO_SCENARIOS } from "./demoData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiClientError extends Error {
  public statusCode?: number;
  public details?: unknown;

  constructor(message: string, statusCode?: number, details?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Check backend API health and connectivity status.
 */
export async function checkBackendHealth(): Promise<{
  online: boolean;
  data?: HealthResponse;
  error?: string;
}> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
      },
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      return {
        online: false,
        error: `Backend returned HTTP status ${res.status}`,
      };
    }

    const data: HealthResponse = await res.json();
    return { online: true, data };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Connection failed";
    return { online: false, error: message };
  }
}

/**
 * Send natural language question and filters to backend POST /query.
 */
export async function executeQuery(
  request: QueryRequest,
  options?: { useDemoFallback?: boolean }
): Promise<QueryResponse> {
  const cleanedQuery = request.query.trim();
  if (!cleanedQuery) {
    throw new ApiClientError("Question query cannot be empty or whitespace.", 400);
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000);

    const res = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        query: cleanedQuery,
        filters: request.filters,
        top_k: request.top_k ?? 5,
        stream: false,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}`;
      try {
        const errorJson = await res.json();
        errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
      } catch {
        // ignore parse error
      }
      throw new ApiClientError(
        `Backend query failed (${res.status}): ${errorDetail}`,
        res.status,
        errorDetail
      );
    }

    const data: QueryResponse = await res.json();
    return data;
  } catch (err: unknown) {
    // If backend is unreachable and demo fallback is allowed, match a demo scenario
    if (options?.useDemoFallback) {
      const match = DEMO_SCENARIOS.find(
        (s) =>
          cleanedQuery.toLowerCase().includes("curing") ||
          s.query.toLowerCase() === cleanedQuery.toLowerCase()
      );
      if (match) {
        return match.response;
      }
      return DEMO_SCENARIOS[0].response;
    }

    if (err instanceof ApiClientError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : "Network error";
    throw new ApiClientError(
      `Failed to connect to Site Shield AI backend at ${API_BASE_URL}. Ensure the backend service is running or toggle Demo Mode. Details: ${message}`
    );
  }
}
