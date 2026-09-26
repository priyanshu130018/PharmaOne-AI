import React from "react";
import { useSelector } from "react-redux";
import { Badge } from "./ui.jsx";
import {
  SEVERITIES,
  DEVIATION_TYPES,
  SEVERITY_STYLES,
  labelFor,
} from "../constants/vocab.js";

function formatWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RecentDeviations() {
  const { list, listStatus } = useSelector((s) => s.deviations);

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
        <h2 className="text-sm font-semibold text-slate-800">Recent deviations</h2>
        <span className="text-xs text-slate-400">
          {listStatus === "loading" ? "Loading…" : `${list.length} shown`}
        </span>
      </header>

      {list.length === 0 ? (
        <p className="px-5 py-6 text-center text-sm text-slate-400">
          No deviations saved yet. Logged deviations will appear here.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {list.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-4 px-5 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-slate-400">{d.reference}</span>
                  <span className="truncate text-sm font-medium text-slate-800">{d.title}</span>
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
                  <span>{labelFor(DEVIATION_TYPES, d.deviation_type)}</span>
                  <span aria-hidden>·</span>
                  <span className="capitalize">{d.status?.replace("_", " ")}</span>
                  <span aria-hidden>·</span>
                  <span>{formatWhen(d.created_at)}</span>
                </div>
              </div>
              {d.severity && (
                <Badge className={SEVERITY_STYLES[d.severity] || "border-slate-200 bg-slate-100 text-slate-600"}>
                  {labelFor(SEVERITIES, d.severity)}
                </Badge>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
