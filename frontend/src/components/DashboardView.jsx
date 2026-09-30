import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchDeviations, fetchSummary } from "../features/deviations/deviationsSlice.js";
import { api } from "../api/client.js";
import { Badge } from "./ui.jsx";
import {
  SEVERITIES,
  DEVIATION_TYPES,
  SEVERITY_STYLES,
  labelFor,
} from "../constants/vocab.js";
import {
  AlertTriangle, CheckCircle2, Clock, ShieldCheck, ArrowRight,
  Package, GitBranch, MessageSquareWarning, RefreshCw, ExternalLink, Layers
} from "./icons.jsx";

const STATUS_STYLES = {
  draft: "bg-slate-100 text-slate-700 border-slate-200",
  submitted: "bg-blue-50 text-blue-700 border-blue-200",
  under_review: "bg-purple-50 text-purple-700 border-purple-200",
  closed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  investigation: "bg-amber-50 text-amber-700 border-amber-200",
  "root cause": "bg-indigo-50 text-indigo-700 border-indigo-200",
  "in progress": "bg-blue-50 text-blue-700 border-blue-200",
  "pending release": "bg-amber-50 text-amber-700 border-amber-200",
};

function formatStatus(status) {
  if (!status) return "Draft";
  const map = {
    draft: "Draft",
    submitted: "Submitted",
    under_review: "Under Review",
    closed: "Closed",
    investigation: "Investigation",
    "root cause": "Root Cause",
    "in progress": "In Progress",
    "pending release": "Pending Release",
  };
  return map[status.toLowerCase()] || status.replace("_", " ");
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DashboardView({ onNavigateToLogDeviation, onNavigate, onRecordClick }) {
  const dispatch = useDispatch();
  const { user } = useSelector((s) => s.auth);
  const { summary, list, listStatus } = useSelector((s) => s.deviations);

  const [qmsMetrics, setQmsMetrics] = useState({
    deviations: 12,
    investigations: 4,
    capas: 3,
    pending_batch_releases: 2,
    complaints: 1,
    actions_required_count: 5,
  });

  const [recentQualityEvents, setRecentQualityEvents] = useState([
    {
      id: "DEV-2026-018",
      type: "deviation",
      title: "Reactor temperature exceeded limit",
      severity: "major",
      status: "Investigation",
      batch: "API-2026-041",
    },
    {
      id: "INV-2026-012",
      type: "investigation",
      title: "Reactor temperature excursion on Batch API-2026-041",
      severity: "major",
      status: "Root Cause",
      batch: "API-2026-041",
    },
    {
      id: "CAPA-2026-009",
      type: "capa",
      title: "Preventive Maintenance Enhancement for Reactor Cooling Valve Actuators",
      severity: "major",
      status: "In Progress",
      batch: "API-2026-041",
    },
    {
      id: "API-2026-041",
      type: "batch",
      title: "Paracetamol API (v4.2)",
      severity: "major",
      status: "Pending Release",
      batch: "API-2026-041",
    },
  ]);

  useEffect(() => {
    dispatch(fetchDeviations());
    dispatch(fetchSummary());

    if (api && typeof api.getDashboardSummary === "function") {
      api.getDashboardSummary()
        .then((data) => {
          if (data) setQmsMetrics(data);
        })
        .catch(() => {});
    }

    if (api && typeof api.getDashboardActivity === "function") {
      api.getDashboardActivity()
        .then((data) => {
          if (data?.recent_events && Array.isArray(data.recent_events) && data.recent_events.length > 0) {
            setRecentQualityEvents(data.recent_events);
          } else if (Array.isArray(data) && data.length > 0) {
            setRecentQualityEvents(data);
          }
        })
        .catch(() => {});
    }
  }, [dispatch]);

  const bySeverity = {};
  (summary?.by_severity ?? []).forEach((r) => {
    bySeverity[r.key] = r.count;
  });

  const byStatus = {};
  (summary?.by_status ?? []).forEach((r) => {
    byStatus[r.key] = r.count;
  });

  const byType = {};
  (summary?.by_type ?? []).forEach((r) => {
    byType[r.key] = r.count;
  });

  const reviewRequiredList = (list || []).filter((d) => d.status !== "closed");
  const totalCount = summary?.total ?? 0;

  return (
    <div className="space-y-6">
      {/* Top Banner / Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Dashboard
            </h1>
            <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-200/60">
              {user?.company_name || "Active Tenant"}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Overview of deviation activity and items requiring attention
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {onNavigate && (
            <button
              type="button"
              onClick={() => onNavigate("batches")}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition"
            >
              <Package className="h-3.5 w-3.5 text-white" />
              <span>Create / View Batch</span>
            </button>
          )}

          <button
            type="button"
            onClick={onNavigateToLogDeviation}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition"
          >
            <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>Log Deviation</span>
          </button>
        </div>
      </div>

      {/* CONNECTED QUALITY LIFECYCLE OVERVIEW BAR */}
      <div className="rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-slate-50 p-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-blue-200/60 pb-2.5 mb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-700" />
            <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
              Connected QMS Lifecycle Overview
            </span>
          </div>
          <span className="text-[11px] font-semibold text-blue-700 bg-blue-100/80 px-2 py-0.5 rounded">
            ChemCorp Bengaluru Site
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <div
            onClick={() => onNavigate?.("deviations")}
            className="p-2.5 bg-white/90 rounded-lg border border-blue-100 hover:border-blue-300 cursor-pointer transition shadow-xs"
          >
            <div className="text-[10px] font-bold uppercase text-slate-500">Open Deviations</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{qmsMetrics.deviations ?? 12}</div>
            <div className="text-[10px] text-blue-600 font-medium mt-0.5 truncate">
              {recentQualityEvents?.find(e => e.reference === "DEV-2026-018" || e.id === "DEV-2026-018")?.severity_or_status === "Closed" 
                ? "DEV-2026-018 Closed" 
                : "DEV-2026-018 Active"}
            </div>
          </div>

          <div
            onClick={() => onNavigate?.("investigation", { deviationId: "DEV-2026-018", investigationId: "INV-2026-012" })}
            className="p-2.5 bg-white/90 rounded-lg border border-blue-100 hover:border-blue-300 cursor-pointer transition shadow-xs"
          >
            <div className="text-[10px] font-bold uppercase text-slate-500">Investigations</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{qmsMetrics.investigations ?? 4}</div>
            <div className="text-[10px] text-indigo-600 font-medium mt-0.5 truncate">
              {recentQualityEvents?.find(e => e.reference === "INV-2026-012" || e.id === "INV-2026-012")?.severity_or_status === "Completed"
                ? "INV-2026-012 Done"
                : "INV-2026-012 Active"}
            </div>
          </div>

          <div
            onClick={() => onNavigate?.("capa", { deviationId: "DEV-2026-018", capaId: "CAPA-2026-009" })}
            className="p-2.5 bg-white/90 rounded-lg border border-blue-100 hover:border-blue-300 cursor-pointer transition shadow-xs"
          >
            <div className="text-[10px] font-bold uppercase text-slate-500">CAPAs</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{qmsMetrics.capas ?? 3}</div>
            <div className="text-[10px] text-emerald-600 font-medium mt-0.5 truncate">
              {recentQualityEvents?.find(e => e.reference === "CAPA-2026-009" || e.id === "CAPA-2026-009")?.severity_or_status === "Completed"
                ? "CAPA-2026-009 Done"
                : "CAPA-2026-009 Active"}
            </div>
          </div>

          <div
            onClick={() => onNavigate?.("batch_release", { batchNumber: "API-2026-041", batchReleaseId: "BR-2026-041" })}
            className="p-2.5 bg-white/90 rounded-lg border border-amber-200/80 bg-amber-50/40 hover:border-amber-300 cursor-pointer transition shadow-xs"
          >
            <div className="text-[10px] font-bold uppercase text-amber-800">Batch Release</div>
            <div className="text-xl font-bold text-amber-900 mt-1">{qmsMetrics.pending_batch_releases ?? 2} pending</div>
            <div className="text-[10px] text-amber-700 font-medium mt-0.5 truncate">
              {recentQualityEvents?.find(e => e.reference?.includes("041") || e.id?.includes("041"))?.severity_or_status === "Released"
                ? "API-2026-041 Released"
                : "API-2026-041 On Hold"}
            </div>
          </div>

          <div
            onClick={() => onNavigate?.("complaints")}
            className="p-2.5 bg-white/90 rounded-lg border border-blue-100 hover:border-blue-300 cursor-pointer transition shadow-xs"
          >
            <div className="text-[10px] font-bold uppercase text-slate-500">Complaints</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{qmsMetrics.complaints ?? 1}</div>
            <div className="text-[10px] text-blue-600 font-medium mt-0.5">COM-2026-003</div>
          </div>

          <div
            onClick={() => onNavigate?.("investigation", { deviationId: "DEV-2026-018", investigationId: "INV-2026-012" })}
            className="p-2.5 bg-white/90 rounded-lg border border-red-200/80 bg-red-50/40 hover:border-red-300 cursor-pointer transition shadow-xs"
          >
            <div className="text-[10px] font-bold uppercase text-red-800">Actions Required</div>
            <div className="text-xl font-bold text-red-900 mt-1">{qmsMetrics.actions_required_count ?? 5}</div>
            <div className="text-[10px] text-red-700 font-medium mt-0.5">Overdue / Blocked</div>
          </div>
        </div>
      </div>

      {/* RECENT QUALITY EVENTS WORKFLOW ROW */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              Recent Quality Events
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Connected lifecycle progression for reference demo scenario
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-400">
            {recentQualityEvents.length} active stages
          </span>
        </div>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                <th className="py-2.5 px-3">Record ID</th>
                <th className="py-2.5 px-3">Event / Context</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Workflow State</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recentQualityEvents.map((evt) => (
                <tr
                  key={evt.id}
                  onClick={() => onRecordClick?.(evt.type || "deviation", evt.id)}
                  className="cursor-pointer hover:bg-blue-50/40 transition group"
                >
                  <td className="py-2.5 px-3 font-mono font-bold text-blue-700 whitespace-nowrap">
                    {evt.id}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="font-semibold text-slate-800" title={evt.title}>{evt.title}</span>
                    <span className="text-[10px] text-slate-400 block">Batch: {evt.batch || "API-2026-041"}</span>
                  </td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <Badge className="bg-amber-50 text-amber-800 border-amber-200">
                      {evt.severity || "Major"}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                        STATUS_STYLES[evt.status?.toLowerCase()] || "bg-slate-100 text-slate-700 border-slate-200"
                      }`}
                    >
                      {evt.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 group-hover:translate-x-0.5 transition"
                    >
                      <span>Open Workspace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SUMMARY CARDS: Total Deviations, Critical, Major, Minor */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {/* Total Deviations */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Total Deviations
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {totalCount}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">Scoped to company</div>
        </div>

        {/* Critical */}
        <div className="rounded-xl border border-red-200 bg-red-50/30 p-4 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-red-700">
            Critical
          </div>
          <div className="mt-2 text-2xl font-bold text-red-800">
            {bySeverity.critical ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-red-600">Immediate QA Review</div>
        </div>

        {/* Major */}
        <div className="rounded-xl border border-amber-200 bg-amber-50/30 p-4 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
            Major
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-800">
            {bySeverity.major ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-amber-600">CQA / CPP impact</div>
        </div>

        {/* Minor */}
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 shadow-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-blue-700">
            Minor
          </div>
          <div className="mt-2 text-2xl font-bold text-blue-800">
            {bySeverity.minor ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-blue-600">Low-risk events</div>
        </div>
      </div>

      {/* MIDDLE SECTION: Two Columns (LEFT: Recent Deviations, RIGHT: Review Required) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 items-start">
        {/* LEFT CARD: Recent Deviations */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Recent Deviations</h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Latest logged quality events in tenant
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-400">
              {list?.length ?? 0} recorded
            </span>
          </div>

          {(!list || list.length === 0) ? (
            <div className="py-8 text-center">
              <p className="text-sm font-medium text-slate-500">No deviations recorded yet.</p>
              <p className="text-xs text-slate-400 mt-1">Start by logging your first deviation event.</p>
              <button
                type="button"
                onClick={onNavigateToLogDeviation}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition"
              >
                Log Deviation
              </button>
            </div>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="py-2.5 px-3">Deviation ID</th>
                    <th className="py-2.5 px-3">Title</th>
                    <th className="py-2.5 px-3">Severity</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {list.map((d) => (
                    <tr key={d.id} className="cursor-default hover:bg-slate-50/60 transition">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-700 whitespace-nowrap">
                        {d.reference}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800 max-w-[180px] truncate" title={d.title}>
                        {d.title}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        {d.severity ? (
                          <Badge className={SEVERITY_STYLES[d.severity] || "border-slate-200 bg-slate-100 text-slate-700"}>
                            {labelFor(SEVERITIES, d.severity)}
                          </Badge>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[d.status] || "border-slate-200 bg-slate-100 text-slate-700"}`}>
                          {formatStatus(d.status)}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-500 whitespace-nowrap font-mono text-[11px]">
                        {formatDate(d.occurred_on || d.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* RIGHT CARD: Review Required */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Review Required</h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Active records pending investigation or approval
              </p>
            </div>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${reviewRequiredList.length > 0 ? "bg-amber-50 text-amber-700 border border-amber-200" : "text-slate-400"}`}>
              {reviewRequiredList.length} pending
            </span>
          </div>

          {reviewRequiredList.length === 0 ? (
            <div className="py-8 text-center">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 mx-auto mb-2">
                ✓
              </div>
              <p className="text-sm font-medium text-slate-700">No deviations currently require review.</p>
              <p className="text-xs text-slate-400 mt-1">All logged records in your company are closed or resolved.</p>
            </div>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="py-2.5 px-3">Deviation ID</th>
                    <th className="py-2.5 px-3">Title</th>
                    <th className="py-2.5 px-3">Severity</th>
                    <th className="py-2.5 px-3">Current State</th>
                    <th className="py-2.5 px-3 text-right">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {reviewRequiredList.map((d) => (
                    <tr key={d.id} className="cursor-default hover:bg-slate-50/60 transition">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-700 whitespace-nowrap">
                        {d.reference}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800 max-w-[180px] truncate" title={d.title}>
                        {d.title}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        {d.severity ? (
                          <Badge className={SEVERITY_STYLES[d.severity] || "border-slate-200 bg-slate-100 text-slate-700"}>
                            {labelFor(SEVERITIES, d.severity)}
                          </Badge>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800">
                          {formatStatus(d.status)}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-500 whitespace-nowrap font-mono text-[11px]">
                        {formatDate(d.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* BOTTOM SECTION: Deviation Activity */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="text-sm font-bold text-slate-900">Deviation Activity</h2>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Real quality distribution across categories and lifecycle processing
          </p>
        </div>

        {totalCount === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No activity recorded yet. Quality trends will be calculated automatically as records are logged.
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Category / Type Distribution */}
            <div className="space-y-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Activity by Deviation Type
              </span>
              <div className="space-y-2.5 pt-1">
                {(summary?.by_type ?? []).map((item) => {
                  const pct = totalCount > 0 ? Math.round((item.count / totalCount) * 100) : 0;
                  return (
                    <div key={item.key} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-700">{labelFor(DEVIATION_TYPES, item.key)}</span>
                        <span className="font-mono text-slate-500">{item.count} ({pct}%)</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 rounded-full transition-all duration-300"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Lifecycle Status Distribution */}
            <div className="space-y-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Activity by Lifecycle Status
              </span>
              <div className="space-y-2.5 pt-1">
                {(summary?.by_status ?? []).map((item) => {
                  const pct = totalCount > 0 ? Math.round((item.count / totalCount) * 100) : 0;
                  return (
                    <div key={item.key} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-700">{formatStatus(item.key)}</span>
                        <span className="font-mono text-slate-500">{item.count} ({pct}%)</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-600 rounded-full transition-all duration-300"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
