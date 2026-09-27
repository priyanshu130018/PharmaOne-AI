// Thin fetch wrapper around the PharmaOne backend API.
//
// The base path defaults to `/api/v1`. In local development Vite proxies `/api`
// to the backend, and in production VITE_API_BASE_URL configures the target API host.
// An optional build-time or runtime override is supported.
const rawBase = (import.meta.env.VITE_API_BASE_URL || "").trim();
const API_BASE = rawBase
  ? rawBase.endsWith("/api/v1")
    ? rawBase
    : `${rawBase.replace(/\/+$/, "")}/api/v1`
  : "/api/v1";

const TOKEN_KEY = "pharmaone_auth_token";

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
    if (body.error && typeof body.error.message === "string") return body.error.message;
    if (body.error && typeof body.error === "string") return body.error;
    if (typeof body.message === "string") return body.message;
  }
  return `Request failed with status ${status}`;
}

function getAuthHeaders() {
  const headers = {};
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      headers["Authorization"] = `Bearer ${token.trim()}`;
    }
  } catch {
    // ignore storage access issues in restricted environments
  }
  return headers;
}

async function request(path, { method = "GET", body, signal, customHeaders = {} } = {}) {
  const headers = { ...getAuthHeaders(), ...customHeaders };
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

async function requestMultipart(path, formData, { signal } = {}) {
  const headers = { ...getAuthHeaders() };
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
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
  // Authentication & Session
  login: ({ email, password }) =>
    request("/auth/login", { method: "POST", body: { email, password } }),

  logout: () => request("/auth/logout", { method: "POST" }),

  me: () => request("/auth/me"),

  getDemoUsers: () => request("/auth/demo-users"),


  // Extract & normalize text from pasted text / email
  extractText: (text, sourceType = "text") =>
    request("/deviations/extract-text", {
      method: "POST",
      body: { text, source_type: sourceType },
    }),

  // Extract & normalize text from an uploaded document (PDF, TXT)
  extractDocument: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return requestMultipart("/deviations/extract-text", formData);
  },

  // AI Deviation Assistant: process raw content -> extraction + risk assessment.
  processDeviation: (content, source = "text") =>
    request("/deviations/process", { method: "POST", body: { content, source } }),

  // AI Deviation Assistant Chat: context-aware chat
  sendDeviationChat: ({ message, context = {}, assessment = null, currentForm = {}, rawContent = null }) =>
    request("/deviations/chat", {
      method: "POST",
      body: {
        message,
        context,
        assessment,
        current_form: currentForm,
        raw_content: rawContent,
      },
    }),

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
