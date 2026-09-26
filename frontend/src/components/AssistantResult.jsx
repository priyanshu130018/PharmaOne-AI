import React from "react";
import { Button, Badge } from "./ui.jsx";
import {
  SEVERITIES,
  IMPACTS,
  DEVIATION_TYPES,
  BATCH_STATUSES,
  SEVERITY_STYLES,
  labelFor,
} from "../constants/vocab.js";

const EXTRACTION_LABELS = {
  title: "Title / Description",
  description: "Detailed Description",
  deviation_type: "Type",
  product_name: "Related Product",
  product_code: "Product Code",
  batch_number: "Batch / Lot",
  manufacturing_stage: "Stage",
  equipment: "Equipment",
  department: "Department",
  parameter: "Parameter",
  expected_condition: "Approved Range",
  actual_condition: "Actual Value",
  duration: "Duration",
  immediate_action: "Immediate Action",
  batch_status: "Batch Status",
};

function displayValue(key, value) {
  if (key === "deviation_type") return labelFor(DEVIATION_TYPES, value);
  if (key === "batch_status") return labelFor(BATCH_STATUSES, value);
  return value;
}

export default function AssistantResult({ extraction, assessment, meta, applied, onApply }) {
  const extractedEntries = extraction
    ? Object.entries(extraction).filter(([, v]) => v !== null && v !== undefined && v !== "")
    : [];

  const recSeverity = assessment?.recommended_severity || assessment?.severity;
  const recImpact = assessment?.recommended_impact || assessment?.impact;
  const reasonText = assessment?.reason || assessment?.severity_reason || assessment?.impact_reason;

  return (
    <div className="space-y-4">
      {/* 1. AI Initial Impact Recommendation */}
      {recImpact && (
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              AI Initial Impact Recommendation
            </span>
            <Badge className="border-brand-200 bg-brand-50 font-semibold text-brand-700">
              {labelFor(IMPACTS, recImpact)}
            </Badge>
          </div>
          <div className="mt-2 text-xs text-slate-700">
            <span className="font-semibold text-slate-600">Reason: </span>
            {assessment.impact_reason || reasonText || "Evaluated against product quality specifications and critical attributes."}
          </div>
        </div>
      )}

      {/* 2. AI Initial Severity Recommendation */}
      {recSeverity && (
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              AI Initial Severity Recommendation
            </span>
            <div className="flex items-center gap-1.5">
              <Badge className={SEVERITY_STYLES[recSeverity] || "border-slate-200 bg-slate-100 text-slate-700"}>
                {labelFor(SEVERITIES, recSeverity)}
              </Badge>
              {meta?.is_stub && (
                <span className="rounded bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                  Heuristic fallback
                </span>
              )}
            </div>
          </div>
          <div className="mt-2 text-xs text-slate-700">
            <span className="font-semibold text-slate-600">Reason: </span>
            {assessment.severity_reason || reasonText || "Provisional classification based on ICH Q9 quality risk management criteria."}
          </div>
        </div>
      )}

      {/* 3. Evidence / References */}
      <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Evidence / References
          </span>
          {meta?.rag_available === false && (
            <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200">
              RAG offline
            </span>
          )}
        </div>

        {/* Retrieved SOP Sources (Vector RAG) */}
        {Array.isArray(meta?.retrieved_sources) && meta.retrieved_sources.length > 0 && (
          <div>
            <p className="mb-1.5 text-[11px] font-semibold text-slate-500">
              Retrieved Reference SOPs (Vector RAG):
            </p>
            <div className="space-y-1.5">
              {meta.retrieved_sources.map((src, i) => (
                <div key={i} className="rounded border border-slate-200 bg-slate-50/70 p-2 text-xs">
                  <div className="flex items-center justify-between font-medium text-slate-800">
                    <span className="truncate pr-2 font-medium">{src.document_name}</span>
                    {src.similarity_score != null && (
                      <span className="shrink-0 rounded bg-brand-50 px-1.5 py-0.5 text-[10px] font-semibold text-brand-700">
                        Match: {Math.round(src.similarity_score * 100)}%
                      </span>
                    )}
                  </div>
                  {src.section && <p className="mt-0.5 text-[11px] text-slate-500">{src.section}</p>}
                  {src.content && (
                    <p className="mt-1 line-clamp-2 text-[11px] italic text-slate-600">
                      "{src.content}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Factual Evidence List */}
        {Array.isArray(assessment?.evidence) && assessment.evidence.length > 0 && (
          <div>
            <p className="mb-1 text-[11px] font-semibold text-slate-500">Observed Evidence Facts:</p>
            <ul className="list-inside list-disc space-y-0.5 text-xs text-slate-600">
              {assessment.evidence.map((ev, i) => (
                <li key={i}>{ev}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Uncertainties & Reviewer Checks */}
        {Array.isArray(assessment?.uncertainties) && assessment.uncertainties.length > 0 && (
          <div>
            <p className="mb-1 text-[11px] font-semibold text-amber-700">
              Uncertainties & Reviewer Checks:
            </p>
            <ul className="list-inside list-disc space-y-0.5 text-xs text-amber-800">
              {assessment.uncertainties.map((u, i) => (
                <li key={i}>{u}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Missing Information Identified */}
        {Array.isArray(meta?.deviation?.missing_information) && meta.deviation.missing_information.length > 0 && (
          <div className="rounded bg-amber-50/60 p-2 border border-amber-200/50">
            <p className="text-[11px] font-semibold text-amber-800 mb-0.5">Missing Fields (AI Identified):</p>
            <p className="text-[11px] text-amber-700">
              {meta.deviation.missing_information.join(", ")}
            </p>
          </div>
        )}
      </div>

      {/* 4. Human Review Required Notice */}
      <div className="rounded-lg border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900">
        <div className="mb-1 flex items-center gap-1.5 font-semibold text-amber-800">
          <svg className="h-4 w-4 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          Human Review Required
        </div>
        <p className="leading-relaxed text-amber-800/90">
          AI output is advisory decision support per ICH Q9 methodology. It does not finalize regulatory classifications.
          A qualified quality reviewer must review and verify all fields on the left before saving.
        </p>
        {assessment?.criteria_note && (
          <p className="mt-2 text-[11px] italic text-amber-700/80 border-t border-amber-200/60 pt-1.5">
            {assessment.criteria_note}
          </p>
        )}
      </div>

      {/* Extracted Fields Summary Table */}
      {extractedEntries.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Extracted Fields Summary
          </p>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1.5 sm:grid-cols-2 text-xs">
            {extractedEntries.map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <dt className="min-w-24 shrink-0 font-medium text-slate-500">
                  {EXTRACTION_LABELS[key] || key}:
                </dt>
                <dd className="text-slate-700 truncate">{displayValue(key, value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Auto-populate status button */}
      <div className="flex items-center justify-between gap-3 rounded-lg bg-brand-50 px-4 py-3">
        <p className="text-xs text-brand-800">
          Fields automatically populated to form. You can freely edit any value on the left.
        </p>
        {onApply && (
          <Button type="button" onClick={onApply} disabled={applied} variant="secondary">
            {applied ? "Populated to Form ✓" : "Re-apply to Form"}
          </Button>
        )}
      </div>
    </div>
  );
}
