import React from "react";

export const WORKFLOW_STAGES = [
  { key: "reported", label: "Reported", description: "Deviation Intake", view: "deviations" },
  { key: "severity", label: "Severity & Impact", description: "Risk Classification", view: "deviations" },
  { key: "investigation", label: "Investigation", description: "Evidence & Tasks", view: "investigation" },
  { key: "root_cause", label: "Root Cause", description: "5 Whys Analysis", view: "root_cause" },
  { key: "capa", label: "CAPA", description: "Corrective & Preventive", view: "capa" },
  { key: "effectiveness", label: "Verification", description: "Effectiveness Check", view: "effectiveness" },
  { key: "closed", label: "Closed", description: "QA Sign-off", view: "closure" },
];

export default function WorkflowStepper({ currentStage = "reported", onStageClick, onNavigate }) {
  // Normalize stage key
  const normalizedStage = currentStage === "closure" ? "closed" : currentStage;
  const stageIndex = WORKFLOW_STAGES.findIndex((s) => s.key === normalizedStage);
  const activeIdx = stageIndex >= 0 ? stageIndex : 0;

  const handleStepClick = (stage) => {
    if (onStageClick) {
      onStageClick(stage.key);
    } else if (onNavigate) {
      onNavigate(stage.view);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 mb-2.5">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
            ⚡
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Quality Event Lifecycle
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px]">
          <span className="text-slate-400">Current Gate:</span>
          <span className="rounded bg-blue-50 px-2 py-0.5 font-bold text-blue-700 border border-blue-200 uppercase text-[10px]">
            {WORKFLOW_STAGES[activeIdx]?.label || currentStage}
          </span>
        </div>
      </div>

      <nav aria-label="Progress">
        <ol className="flex items-center justify-between gap-1 sm:gap-2">
          {WORKFLOW_STAGES.map((stage, idx) => {
            const isCompleted = idx < activeIdx || (normalizedStage === "closed" && idx === WORKFLOW_STAGES.length - 1);
            const isCurrent = idx === activeIdx && normalizedStage !== "closed";

            return (
              <li key={stage.key} className="relative flex-1">
                <button
                  type="button"
                  onClick={() => handleStepClick(stage)}
                  className={`group flex w-full flex-col items-center p-1.5 rounded-lg text-center transition ${
                    isCurrent
                      ? "bg-blue-50 border border-blue-200 text-blue-800 font-semibold"
                      : isCompleted
                      ? "bg-slate-50 hover:bg-slate-100 text-slate-800"
                      : "opacity-60 text-slate-400 hover:opacity-80"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                        isCompleted
                          ? "bg-emerald-600 text-white"
                          : isCurrent
                          ? "bg-blue-600 text-white ring-3 ring-blue-100"
                          : "border border-slate-300 bg-white text-slate-500"
                      }`}
                    >
                      {isCompleted ? "✓" : idx + 1}
                    </span>
                    <span className="hidden sm:inline text-xs font-medium truncate max-w-[85px] lg:max-w-none">
                      {stage.label}
                    </span>
                  </div>
                  <span className="mt-0.5 text-[9px] text-slate-500 hidden md:block truncate">
                    {stage.description}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
}
