import React from "react";
import { useSelector } from "react-redux";

function Stat({ label, value }) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-white/10 px-3 py-1.5 text-center">
      <span className="text-lg font-semibold leading-none text-white">{value}</span>
      <span className="mt-0.5 text-[10px] uppercase tracking-wide text-brand-100">{label}</span>
    </div>
  );
}

export default function Header() {
  const summary = useSelector((s) => s.deviations.summary);
  const bySeverity = {};
  (summary?.by_severity ?? []).forEach((r) => {
    bySeverity[r.key] = r.count;
  });

  return (
    <header className="bg-gradient-to-r from-brand-800 to-brand-600 text-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 text-lg font-bold">
            P1
          </div>
          <div>
            <h1 className="text-lg font-semibold leading-tight">PharmaOne AI</h1>
            <p className="text-xs text-brand-100">AI-Powered Deviation Intake</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Stat label="Total" value={summary?.total ?? "—"} />
          <Stat label="Critical" value={bySeverity.critical ?? 0} />
          <Stat label="Major" value={bySeverity.major ?? 0} />
          <Stat label="Minor" value={bySeverity.minor ?? 0} />
        </div>
      </div>
    </header>
  );
}
