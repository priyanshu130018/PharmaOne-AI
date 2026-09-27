import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, API_BASE } from "../client.js";

describe("Frontend API Client Base URL and Endpoints", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("API_BASE resolves to /api/v1 when VITE_API_BASE_URL is empty", () => {
    expect(API_BASE).toBe("/api/v1");
  });

  it("calls listDeviations with /api/v1/deviations?limit=8", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ items: [], total: 0 }),
    });

    const result = await api.listDeviations({ limit: 8 });
    expect(fetchSpy).toHaveBeenCalledWith("/api/v1/deviations?limit=8", expect.any(Object));
    expect(result).toEqual({ items: [], total: 0 });
  });

  it("calls getReportSummary with /api/v1/reports/summary", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ total: 5, open: 2 }),
    });

    const result = await api.getReportSummary();
    expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/summary", expect.any(Object));
    expect(result).toEqual({ total: 5, open: 2 });
  });

  it("calls extractText with /api/v1/deviations/extract-text", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ text: "Sample excursion" }),
    });

    const result = await api.extractText("Sample excursion");
    expect(fetchSpy).toHaveBeenCalledWith("/api/v1/deviations/extract-text", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ text: "Sample excursion", source_type: "text" }),
    }));
    expect(result).toEqual({ text: "Sample excursion" });
  });

  it("calls health with /api/v1/health", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ status: "ok" }),
    });

    const result = await api.health();
    expect(fetchSpy).toHaveBeenCalledWith("/api/v1/health", expect.any(Object));
    expect(result).toEqual({ status: "ok" });
  });

  it("calls sendDeviationChat with /api/v1/deviations/chat", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ response: "Autoclave AC-02" }),
    });

    const result = await api.sendDeviationChat({
      message: "What equipment was involved?",
      context: { equipment: "Autoclave AC-02" },
    });
    expect(fetchSpy).toHaveBeenCalledWith("/api/v1/deviations/chat", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        message: "What equipment was involved?",
        context: { equipment: "Autoclave AC-02" },
        assessment: null,
        current_form: {},
        raw_content: null,
      }),
    }));
    expect(result).toEqual({ response: "Autoclave AC-02" });
  });
});
