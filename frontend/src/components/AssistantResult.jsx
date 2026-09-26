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
  title: "Title",
  description: "Description",
  deviation_type: "Type",
  product_name: "Product",
  product_code: "Product code",
  batch_number: "Batch",
  manufacturing_stage: "Stage",
  equipment: "Equipment",
  department: "Department",
  responsible_team: "Team",
  expected_condition: "Expected",
  actual_condition: "Actual",
  duration: "Duration",
  parameter: "Parameter",
  immediate_action: "Immediate action",
  batch_status: "Batch status",
};

function displayValue(key, value) {
  if (key === "deviation_type") return labelFor(DEVIATION_TYPES, value);
  if (key === "batch_status") return labelFor(BATCH_STATUSES, value);
  return value;
}

function List({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</p>
      <ul className="list-inside list-disc space-y-0.5 text-sm text-slate-600">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AssistantResult({ extraction, assessment, meta, applied, onApply }) {
  const extractedEntries = extraction
    ? Object.entries(extraction).filter(([, v]) => v !== null && v !== undefined && v !== "")
    : [];

  return (
    <div className="space-y-4">
      {assessment && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-slate-700">Risk assessment</span>
            <Badge className={SEVERITY_STYLES[assessment.recommended_severity] || "bg-slate-100 text-slate-600 border-slate-200"}>
              {labelFor(SEVERITIES, assessment.recommended_severity)}
            </Badge>
            <Badge className="border-brand-200 bg-brand-50 text-brand-700">
              {labelFor(IMPACTS, assessment.recommended_impact)}
            </Badge>
            {meta?.is_stub && (
              <Badge className="border-amber-200 bg-amber-50 text-amber-700">
                Heuristic stub
              </Badge>
            )}
          </div>

          {assessment.reason && <p className="text-sm text-slate-700">{assessment.reason}</p>}

          <div className="mt-3 space-y-3">
            <List title="Evidence" items={assessment.evidence} />
            <List title="Deterministic checks" items={assessment.deterministic_checks} />
            <List title="Retrieved sources" items={assessment.retrieved_sources} />
          </div>

          {assessment.criteria_note && (
            <p className="mt-3 rounded border border-slate-200 bg-white px-2 py-1 text-xs italic text-slate-500">
              {assessment.criteria_note}
            </p>
          )}
        </div>
      )}

      {extractedEntries.length > 0 && (
        <div className="rounded-lg border border-slate-200 p-4">
          <p className="mb-2 text-sm font-semibold text-slate-700">Extracted fields</p>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
            {extractedEntries.map(([key, value]) => (
              <div key={key} className="flex gap-2 text-sm">
                <dt className="min-w-24 shrink-0 font-medium text-slate-500">
                  {EXTRACTION_LABELS[key] || key}
                </dt>
                <dd className="text-slate-700">{displayValue(key, value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 rounded-lg bg-brand-50 px-4 py-3">
        <p className="text-xs text-brand-800">
          Decision support only — a human must review before saving.
        </p>
        <Button type="button" onClick={onApply} disabled={applied}>
          {applied ? "Applied to form ✓" : "Apply to form"}
        </Button>
      </div>
    </div>
  );
}
