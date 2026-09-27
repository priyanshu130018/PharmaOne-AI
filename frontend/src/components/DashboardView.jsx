import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchDeviations, fetchSummary } from "../features/deviations/deviationsSlice.js";
import { Badge } from "./ui.jsx";
import {
  SEVERITIES,
  DEVIATION_TYPES,
  SEVERITY_STYLES,
  labelFor,
} from "../constants/vocab.js";

const STATUS_STYLES = {
  draft: "bg-slate-100 text-slate-700 border-slate-200",
  submitted: "bg-blue-50 text-blue-700 border-blue-200",
  under_review: "bg-purple-50 text-purple-700 border-purple-200",
  closed: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

function formatStatus(status) {
  if (!status) return "Draft";
  const map = {
    draft: "Draft",
    submitted: "Submitted",
    under_review: "Under Review",
    closed: "Closed",
  };
  return map[status] || status.replace("_", " ");
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

export default function DashboardView({ onNavigateToLogDeviation }) {
  const dispatch = useDispatch();
  const { user } = useSelector((s) => s.auth);
  const { summary, list, listStatus } = useSelector((s) => s.deviations);

  useEffect(() => {
    dispatch(fetchDeviations());
    dispatch(fetchSummary());
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

  // Review Required: Deviations requiring attention/review based on existing data model states
  // In the existing schema, deviations with status != 'closed' (e.g. 'submitted', 'under_review', 'draft') require attention
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

        <button
          type="button"
          onClick={onNavigateToLogDeviation}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Log Deviation
        </button>
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
