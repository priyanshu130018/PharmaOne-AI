// Thin fetch wrapper around the PharmaOne backend API.
//
// The base path is RELATIVE (`/api/v1`) on purpose: the browser calls the same
// origin it was served from, and the reverse proxy (nginx in production, Vite in
// dev) forwards `/api` to the backend. This means the backend host/port are never
// hardcoded into the frontend bundle. An optional build-time override is available
// via `VITE_API_BASE_URL` for non-standard deployments.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function extractMessage(status, body) {
  if (body && typeof body === "object") {
    if (typeof body.detail === "string") return body.detail;
    // FastAPI validation errors: detail is a list of {loc, msg, type}
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((e) => {
          const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "field";
          return `${field}: ${e.msg}`;
        })
        .join("; ");
    }
    if (typeof body.message === "string") return body.message;
  }
  return `Request failed with status ${status}`;
}

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = {};
  let payload;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: payload,
    signal,
  });

  if (res.status === 204) return null;

  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(extractMessage(res.status, data), res.status, data);
  }
  return data;
}

export const api = {
  // AI Deviation Assistant: process raw content -> extraction + risk assessment.
  processDeviation: (content, source = "text") =>
    request("/deviations/process", { method: "POST", body: { content, source } }),

  // Persist a final, user-reviewed deviation.
  createDeviation: (payload) =>
    request("/deviations", { method: "POST", body: payload }),

  listDeviations: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.append(k, v);
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/deviations${suffix}`);
  },

  getReportSummary: () => request("/reports/summary"),

  health: () => request("/health"),
};

export { ApiError, API_BASE };
