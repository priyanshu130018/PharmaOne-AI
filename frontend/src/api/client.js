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

  getDeviation: (id) => request(`/deviations/${id}`),

  updateDeviation: (id, payload) =>
    request(`/deviations/${id}`, { method: "PUT", body: payload }),

  confirmDeviationSeverity: (deviationId, payload) =>
    request(`/deviations/${deviationId}/confirm-severity`, { method: "POST", body: payload }),

  listDeviations: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.append(k, v);
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/deviations${suffix}`);
  },

  getReportSummary: () => request("/reports/summary"),

  // QMS Lifecycle Endpoints
  getDashboardSummary: () => request("/dashboard/summary"),
  getDashboardActivity: () => request("/dashboard/activity"),

  // Batches & Manufacturing
  listBatches: () => request("/batches"),
  createBatch: (payload) => request("/batches", { method: "POST", body: payload }),
  getBatch: (id) => request(`/batches/${id}`),
  addManufacturingStep: (batchId, payload) =>
    request(`/batches/${batchId}/steps`, { method: "POST", body: payload }),
  getBatchProcessChecks: (batchId) => request(`/batches/${batchId}/process-checks`),
  createProcessCheck: (batchId, payload) =>
    request(`/batches/${batchId}/process-checks`, { method: "POST", body: payload }),
  createRawMaterial: (payload) => request("/raw-materials", { method: "POST", body: payload }),
  getAuditTrail: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.append(k, v);
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/audit-trail${suffix}`);
  },

  // Investigation Workflow
  startInvestigation: (deviationId) =>
    request(`/deviations/${deviationId}/start-investigation`, { method: "POST" }),
  getInvestigation: (id) => request(`/investigations/${id}`),
  addInvestigationTask: (investigationId, payload) =>
    request(`/investigations/${investigationId}/tasks`, { method: "POST", body: payload }),
  updateInvestigationTask: (investigationId, taskId, payload) =>
    request(`/investigations/${investigationId}/tasks/${taskId}`, { method: "PATCH", body: payload }),
  addInvestigationEvidence: (investigationId, payload) =>
    request(`/investigations/${investigationId}/evidence`, { method: "POST", body: payload }),
  confirmRootCause: (investigationId, payload) =>
    request(`/investigations/${investigationId}/root-cause`, { method: "POST", body: payload }),
  completeInvestigation: (investigationId, payload) =>
    request(`/investigations/${investigationId}/complete`, { method: "POST", body: payload }),

  // CAPA
  createCapa: (payload) => request("/capas", { method: "POST", body: payload }),
  getCapa: (id) => request(`/capas/${id}`),
  addCapaAction: (capaId, payload) =>
    request(`/capas/${capaId}/actions`, { method: "POST", body: payload }),
  updateCapaAction: (capaId, actionId, payload) =>
    request(`/capas/${capaId}/actions/${actionId}`, { method: "PATCH", body: payload }),
  recordEffectiveness: (capaId, payload) =>
    request(`/capas/${capaId}/effectiveness`, { method: "POST", body: payload }),

  // Closure
  closeDeviation: (deviationId, payload) =>
    request(`/deviations/${deviationId}/close`, { method: "POST", body: payload }),

  // Linked Records
  getLinkedRecords: (deviationId) =>
    request(`/deviations/${deviationId}/linked-records`),

  // Batch Release
  getBatchRelease: (id) => request(`/batch-releases/${id}`),
  decideBatchRelease: (id, payload) =>
    request(`/batch-releases/${id}/decision`, { method: "POST", body: payload }),

  // Complaints & Suppliers
  listComplaints: () => request("/complaints"),
  listSuppliers: () => request("/suppliers"),
  listRawMaterials: () => request("/raw-materials"),

  // AI Quality Assistant Actions
  aiSuggestInvestigation: (payload) =>
    request("/ai/investigation/suggest", { method: "POST", body: payload }),
  aiGenerate5Whys: (payload) =>
    request("/ai/root-cause/generate", { method: "POST", body: payload }),
  aiSuggestCapa: (payload) =>
    request("/ai/capa/suggest", { method: "POST", body: payload }),
  aiSummarizeEffectiveness: (payload) =>
    request("/ai/effectiveness/summarize", { method: "POST", body: payload }),
  aiDraftClosure: (payload) =>
    request("/ai/closure/draft", { method: "POST", body: payload }),

  health: () => request("/health"),
};

export const {
  createDeviation,
  getDeviation,
  updateDeviation,
  listDeviations,
  getReportSummary,
  getDashboardSummary,
  getDashboardActivity,
  listBatches,
  createBatch,
  getBatch,
  addManufacturingStep,
  getBatchProcessChecks,
  createProcessCheck,
  createRawMaterial,
  getAuditTrail,
  startInvestigation,
  getInvestigation,
  addInvestigationTask,
  updateInvestigationTask,
  addInvestigationEvidence,
  confirmRootCause,
  completeInvestigation,
  createCapa,
  getCapa,
  addCapaAction,
  updateCapaAction,
  recordEffectiveness,
  closeDeviation,
  getLinkedRecords,
  getBatchRelease,
  decideBatchRelease,
  listComplaints,
  listSuppliers,
  listRawMaterials,
  aiSuggestInvestigation,
  aiGenerate5Whys,
  aiSuggestCapa,
  aiSummarizeEffectiveness,
  aiDraftClosure,
  health,
} = api;

// Aliases for component convenience
export const getDeviationLinkedRecords = (id) => api.getLinkedRecords(id);
export const getAuditLogs = () => api.getDashboardActivity();
export const saveInvestigationRootCause = (id, payload) => api.confirmRootCause(id, payload);
export const recordCapaEffectiveness = (id, payload) => api.recordEffectiveness(id, payload);
export const getComplaints = () => api.listComplaints();
export const getSuppliers = () => api.listSuppliers();
export const getRawMaterials = () => api.listRawMaterials();
export const aiSuggestInvestigationPlan = (invId, devId) =>
  api.aiSuggestInvestigation({ investigation_id: invId, deviation_id: devId });
export const aiSuggestCapaActions = (capaId, rootCause, devId) =>
  api.aiSuggestCapa({ capa_id: capaId, root_cause: rootCause, deviation_id: devId });
export const aiDraftClosureSummary = (devId) =>
  api.aiDraftClosure({ deviation_id: devId });

export { ApiError, API_BASE };

