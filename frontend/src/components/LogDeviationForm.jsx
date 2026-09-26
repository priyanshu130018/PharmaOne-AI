import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  updateField,
  resetForm,
  saveDeviation,
  fetchDeviations,
  fetchSummary,
} from "../features/deviations/deviationsSlice.js";
import { buildCreatePayload, validateForm } from "../features/deviations/payload.js";
import {
  DEVIATION_TYPES,
  SEVERITIES,
  IMPACTS,
  BATCH_STATUSES,
  SOURCES,
} from "../constants/vocab.js";
import { Field, TextInput, TextArea, Select, Button, SectionHeading } from "./ui.jsx";

export default function LogDeviationForm() {
  const dispatch = useDispatch();
  const { form, aiSnapshot, saveStatus, saveError, lastSaved } = useSelector(
    (s) => s.deviations
  );
  const [errors, setErrors] = useState({});

  const set = (name) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    dispatch(updateField({ name, value }));
  };

  const aiApplied = Boolean(aiSnapshot);
  const saving = saveStatus === "loading";

  const handleSubmit = (e) => {
    e.preventDefault();
    const found = validateForm(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    dispatch(saveDeviation(buildCreatePayload(form, aiSnapshot)))
      .unwrap()
      .then(() => {
        dispatch(fetchDeviations());
        dispatch(fetchSummary());
      })
      .catch(() => {});
  };

  return (
    <section className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Log Deviation</h2>
          <p className="text-xs text-slate-500">
            Record a deviation. Fields marked * are required.
          </p>
        </div>
        {aiApplied && (
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
            AI suggestions applied
          </span>
        )}
      </header>

      <form
        onSubmit={handleSubmit}
        className="flex min-h-0 flex-1 flex-col"
        noValidate
      >
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <div className="space-y-3">
            <SectionHeading>Event</SectionHeading>
            <Field label="Title" htmlFor="title" required error={errors.title}>
              <TextInput id="title" value={form.title} onChange={set("title")}
                placeholder="Short summary of the deviation" maxLength={255} />
            </Field>
            <Field label="Description" htmlFor="description" required error={errors.description}>
              <TextArea id="description" value={form.description} onChange={set("description")}
                rows={4} placeholder="What happened, where, and when" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Deviation type" htmlFor="deviation_type" required error={errors.deviation_type}>
                <Select id="deviation_type" value={form.deviation_type} onChange={set("deviation_type")}
                  options={DEVIATION_TYPES} placeholder="Select type…" />
              </Field>
              <Field label="Manufacturing stage" htmlFor="manufacturing_stage">
                <TextInput id="manufacturing_stage" value={form.manufacturing_stage}
                  onChange={set("manufacturing_stage")} placeholder="e.g. Filling" />
              </Field>
            </div>
          </div>
          <div className="space-y-3">
            <SectionHeading>Identification</SectionHeading>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Source" htmlFor="source">
                <Select id="source" value={form.source} onChange={set("source")} options={SOURCES} />
              </Field>
              <Field label="Reported by" htmlFor="reported_by">
                <TextInput id="reported_by" value={form.reported_by} onChange={set("reported_by")}
                  placeholder="Name or user id" />
              </Field>
              <Field label="Occurred on" htmlFor="occurred_on">
                <TextInput id="occurred_on" type="date" value={form.occurred_on}
                  onChange={set("occurred_on")} />
              </Field>
              <Field label="Detected on" htmlFor="detected_on">
                <TextInput id="detected_on" type="date" value={form.detected_on}
                  onChange={set("detected_on")} />
              </Field>
              <Field label="Department" htmlFor="department">
                <TextInput id="department" value={form.department} onChange={set("department")}
                  placeholder="e.g. Warehouse" />
              </Field>
              <Field label="Responsible team" htmlFor="responsible_team">
                <TextInput id="responsible_team" value={form.responsible_team}
                  onChange={set("responsible_team")} placeholder="e.g. QA" />
              </Field>
            </div>
          </div>
          <div className="space-y-3">
            <SectionHeading>Product</SectionHeading>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Product name" htmlFor="product_name">
                <TextInput id="product_name" value={form.product_name} onChange={set("product_name")} />
              </Field>
              <Field label="Product code" htmlFor="product_code">
                <TextInput id="product_code" value={form.product_code} onChange={set("product_code")} />
              </Field>
              <Field label="Batch number" htmlFor="batch_number">
                <TextInput id="batch_number" value={form.batch_number} onChange={set("batch_number")} />
              </Field>
            </div>
            <Field label="Equipment" htmlFor="equipment">
              <TextInput id="equipment" value={form.equipment} onChange={set("equipment")}
                placeholder="e.g. Mixing pump, line 2" />
            </Field>
          </div>

          <div className="space-y-3">
            <SectionHeading>Conditions</SectionHeading>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Expected condition" htmlFor="expected_condition">
                <TextArea id="expected_condition" rows={2} value={form.expected_condition}
                  onChange={set("expected_condition")} />
              </Field>
              <Field label="Actual condition" htmlFor="actual_condition">
                <TextArea id="actual_condition" rows={2} value={form.actual_condition}
                  onChange={set("actual_condition")} />
              </Field>
              <Field label="Parameter" htmlFor="parameter">
                <TextInput id="parameter" value={form.parameter} onChange={set("parameter")}
                  placeholder="e.g. Temperature" />
              </Field>
              <Field label="Duration" htmlFor="duration">
                <TextInput id="duration" value={form.duration} onChange={set("duration")}
                  placeholder="e.g. 45 minutes" />
              </Field>
            </div>
          </div>
          <div className="space-y-3">
            <SectionHeading>Immediate response</SectionHeading>
            <Field label="Immediate action" htmlFor="immediate_action">
              <TextArea id="immediate_action" rows={2} value={form.immediate_action}
                onChange={set("immediate_action")} placeholder="Action taken at time of detection" />
            </Field>
            <div className="grid grid-cols-2 items-end gap-3">
              <Field label="Batch status" htmlFor="batch_status">
                <Select id="batch_status" value={form.batch_status} onChange={set("batch_status")}
                  options={BATCH_STATUSES} placeholder="Select…" />
              </Field>
              <label className="mb-2 inline-flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={Boolean(form.qa_notified)}
                  onChange={set("qa_notified")}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-300" />
                QA notified
              </label>
            </div>
          </div>

          <div className="space-y-3">
            <SectionHeading>Assessment (reviewed)</SectionHeading>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Severity" htmlFor="severity"
                help="Configurable/demo criteria — not a regulatory lookup.">
                <Select id="severity" value={form.severity} onChange={set("severity")}
                  options={SEVERITIES} placeholder="Select…" />
              </Field>
              <Field label="Impact" htmlFor="impact">
                <Select id="impact" value={form.impact} onChange={set("impact")}
                  options={IMPACTS} placeholder="Select…" />
              </Field>
            </div>
            <Field label="Assessment reason" htmlFor="assessment_reason">
              <TextArea id="assessment_reason" rows={2} value={form.assessment_reason}
                onChange={set("assessment_reason")} placeholder="Rationale for the classification" />
            </Field>
          </div>
        </div>
        <div className="space-y-3 border-t border-slate-200 px-5 py-4">
          {saveStatus === "succeeded" && lastSaved && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              Saved as <span className="font-semibold">{lastSaved.reference}</span> (status:{" "}
              {lastSaved.status}). The form has been cleared for the next entry.
            </div>
          )}
          {saveStatus === "failed" && saveError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {saveError}
            </div>
          )}
          <div className="flex items-center justify-end gap-3">
            <Button type="button" variant="secondary"
              onClick={() => { setErrors({}); dispatch(resetForm()); }} disabled={saving}>
              Reset
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save deviation"}
            </Button>
          </div>
        </div>
      </form>
    </section>
  );
}
