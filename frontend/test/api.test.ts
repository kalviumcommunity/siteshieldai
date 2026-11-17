import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { checkBackendHealth, executeQuery, ApiClientError } from "@/lib/api";
import { DEMO_SCENARIOS } from "@/lib/demoData";

describe("Frontend API Service Layer", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("checkBackendHealth returns online: true when HTTP 200", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        service: "Site Shield AI",
        version: "0.1.0",
        environment: "development",
      }),
    });

    const result = await checkBackendHealth();
    expect(result.online).toBe(true);
    expect(result.data?.service).toBe("Site Shield AI");
  });

  it("checkBackendHealth returns online: false on network error", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("ECONNREFUSED"));

    const result = await checkBackendHealth();
    expect(result.online).toBe(false);
    expect(result.error).toContain("ECONNREFUSED");
  });

  it("executeQuery rejects empty or whitespace query with ApiClientError", async () => {
    await expect(executeQuery({ query: "   " })).rejects.toThrow(ApiClientError);
  });

  it("executeQuery sends valid POST request and returns QueryResponse", async () => {
    const mockResponse = DEMO_SCENARIOS[0].response;
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await executeQuery({
      query: "What is curing duration?",
      filters: { project_id: "#104", include_superseded: false },
      top_k: 3,
    });

    expect(result.query_id).toBe(mockResponse.query_id);
    expect(result.status).toBe("supported");
    expect(result.citations.length).toBeGreaterThan(0);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("executeQuery falls back to demo scenarios when demo mode is enabled", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Network connection lost"));

    const result = await executeQuery(
      { query: "What is the minimum curing duration for foundation slabs?" },
      { useDemoFallback: true }
    );

    expect(result.status).toBe("supported");
    expect(result.answer).toContain("14 days");
    expect(result.citations.length).toBe(2);
  });

  it("executeQuery surfaces HTTP error status from backend", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Query parameter cannot be blank." }),
    });

    await expect(
      executeQuery({ query: "invalid" }, { useDemoFallback: false })
    ).rejects.toThrow(/Backend query failed \(422\)/);
  });
});
