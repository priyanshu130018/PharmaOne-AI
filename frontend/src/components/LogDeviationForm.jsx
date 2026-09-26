import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  updateField,
  resetForm,
  saveDeviation,
  fetchDeviations,
  fetchSummary,
} from "../features/deviations/deviationsSlice.js";
import { buildCreatePayload, validateForm, isFormValid } from "../features/deviations/payload.js";
import {
  DEVIATION_TYPES,
  SEVERITIES,
  IMPACTS,
  BATCH_STATUSES,
  SOURCES,
  SEVERITY_STYLES,
  labelFor,
} from "../constants/vocab.js";
import {
  Field,
  TextInput,
  TextArea,
  Select,
  Button,
  SectionHeading,
  Badge,
  AiFieldBadge,
} from "./ui.jsx";

export default function LogDeviationForm() {
  const dispatch = useDispatch();
  const { form, aiFields = {}, userEditedFields = {}, aiSnapshot, saveStatus, saveError, lastSaved } = useSelector(
    (s) => s.deviations
  );
  const [errors, setErrors] = useState({});

  const set = (name) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    dispatch(updateField({ name, value }));
    // Clear field-specific error once touched
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const aiFieldCount = Object.keys(aiFields).length;
  const userOverrideCount = Object.keys(userEditedFields).length;
  const saving = saveStatus === "loading";
  const canSave = isFormValid(form);

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
        setErrors({});
      })
      .catch(() => {});
  };

  return (
    <section
      aria-label="Log Deviation Form"
      className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      {/* Panel Header */}
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-800">Log Deviation</h2>
            {aiFieldCount > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 border border-brand-200/80 px-2.5 py-0.5 text-xs font-medium text-brand-700">
                <svg className="h-3 w-3 text-brand-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" />
                </svg>
                AI suggestions applied ({aiFieldCount})
              </span>
            )}
            {userOverrideCount > 0 && (
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                {userOverrideCount} user edits
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            AIVOA Log Deviation workflow. Review, verify, and edit fields before saving.
          </p>
        </div>

        {form.severity && (
          <Badge className={SEVERITY_STYLES[form.severity] || "bg-slate-100 text-slate-700"}>
            Severity: {labelFor(SEVERITIES, form.severity)}
          </Badge>
        )}
      </header>

      {/* Scrollable Form Body */}
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col" noValidate>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
          
          {/* Section 1: AIVOA Primary Event & Classification */}
          <div className="space-y-3">
            <SectionHeading>1. Event & Classification</SectionHeading>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Site / Plant"
                htmlFor="site_plant"
                badge={<AiFieldBadge isAi={aiFields.site_plant} isUserEdited={userEditedFields.site_plant} />}
              >
                <TextInput
                  id="site_plant"
                  value={form.site_plant}
                  onChange={set("site_plant")}
                  placeholder="e.g. Plant 1 - Sterile Operations"
                />
              </Field>

              <Field
                label="Date of Occurrence"
                htmlFor="occurred_on"
                badge={<AiFieldBadge isAi={aiFields.occurred_on} isUserEdited={userEditedFields.occurred_on} />}
              >
                <TextInput
                  id="occurred_on"
                  type="date"
                  value={form.occurred_on}
                  onChange={set("occurred_on")}
                />
              </Field>
            </div>

            <Field
              label="Title / Short Description"
              htmlFor="title"
              required
              error={errors.title}
              badge={<AiFieldBadge isAi={aiFields.title} isUserEdited={userEditedFields.title} />}
            >
              <TextInput
                id="title"
                value={form.title}
                onChange={set("title")}
                placeholder="Short summary of the deviation (min 3 characters)"
                maxLength={255}
              />
            </Field>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Source Channel"
                htmlFor="source"
                badge={<AiFieldBadge isAi={aiFields.source} isUserEdited={userEditedFields.source} />}
              >
                <Select
                  id="source"
                  value={form.source}
                  onChange={set("source")}
                  options={SOURCES}
                />
              </Field>

              <Field
                label="Deviation Type"
                htmlFor="deviation_type"
                required
                error={errors.deviation_type}
                badge={<AiFieldBadge isAi={aiFields.deviation_type} isUserEdited={userEditedFields.deviation_type} />}
              >
                <Select
                  id="deviation_type"
                  value={form.deviation_type}
                  onChange={set("deviation_type")}
                  options={DEVIATION_TYPES}
                  placeholder="Select type…"
                />
              </Field>
            </div>

            <Field
              label="Detailed Description"
              htmlFor="description"
              required
              error={errors.description}
              badge={<AiFieldBadge isAi={aiFields.description} isUserEdited={userEditedFields.description} />}
            >
              <TextArea
                id="description"
                rows={4}
                value={form.description}
                onChange={set("description")}
                placeholder="Describe what occurred, where, and observed impacts (min 10 characters)"
              />
            </Field>
          </div>

          {/* Section 2: Product & Batch Identification */}
          <div className="space-y-3">
            <SectionHeading>2. Product & Batch Identification</SectionHeading>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Related Product / Material"
                htmlFor="product_name"
                badge={<AiFieldBadge isAi={aiFields.product_name} isUserEdited={userEditedFields.product_name} />}
              >
                <TextInput
                  id="product_name"
                  value={form.product_name}
                  onChange={set("product_name")}
                  placeholder="e.g. Sterile Saline Injection 100mL"
                />
              </Field>

              <Field
                label="Batch / Lot Number"
                htmlFor="batch_number"
                badge={<AiFieldBadge isAi={aiFields.batch_number} isUserEdited={userEditedFields.batch_number} />}
              >
                <TextInput
                  id="batch_number"
                  value={form.batch_number}
                  onChange={set("batch_number")}
                  placeholder="e.g. LOT-2026-042"
                />
              </Field>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field
                label="Equipment / Asset"
                htmlFor="equipment"
                badge={<AiFieldBadge isAi={aiFields.equipment} isUserEdited={userEditedFields.equipment} />}
              >
                <TextInput
                  id="equipment"
                  value={form.equipment}
                  onChange={set("equipment")}
                  placeholder="e.g. Autoclave AC-02"
                />
              </Field>

              <Field
                label="Department"
                htmlFor="department"
                badge={<AiFieldBadge isAi={aiFields.department} isUserEdited={userEditedFields.department} />}
              >
                <TextInput
                  id="department"
                  value={form.department}
                  onChange={set("department")}
                  placeholder="e.g. Sterile Manufacturing"
                />
              </Field>

              <Field
                label="Manufacturing Stage"
                htmlFor="manufacturing_stage"
                badge={<AiFieldBadge isAi={aiFields.manufacturing_stage} isUserEdited={userEditedFields.manufacturing_stage} />}
              >
                <TextInput
                  id="manufacturing_stage"
                  value={form.manufacturing_stage}
                  onChange={set("manufacturing_stage")}
                  placeholder="e.g. Terminal Sterilization"
                />
              </Field>
            </div>
          </div>

          {/* Section 3: Extracted Technical Parameters */}
          <div className="space-y-3">
            <SectionHeading>3. Technical Parameters & Excursion Scope</SectionHeading>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Parameter"
                htmlFor="parameter"
                badge={<AiFieldBadge isAi={aiFields.parameter} isUserEdited={userEditedFields.parameter} />}
              >
                <TextInput
                  id="parameter"
                  value={form.parameter}
                  onChange={set("parameter")}
                  placeholder="e.g. Chamber Temperature, Pressure, pH"
                />
              </Field>

              <Field
                label="Duration"
                htmlFor="duration"
                badge={<AiFieldBadge isAi={aiFields.duration} isUserEdited={userEditedFields.duration} />}
              >
                <TextInput
                  id="duration"
                  value={form.duration}
                  onChange={set("duration")}
                  placeholder="e.g. 6 minutes, 2 hours"
                />
              </Field>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Approved Range"
                htmlFor="expected_condition"
                badge={<AiFieldBadge isAi={aiFields.expected_condition} isUserEdited={userEditedFields.expected_condition} />}
              >
                <TextInput
                  id="expected_condition"
                  value={form.expected_condition}
                  onChange={set("expected_condition")}
                  placeholder="e.g. 121.1°C +/- 0.5°C"
                />
              </Field>

              <Field
                label="Actual Value"
                htmlFor="actual_condition"
                badge={<AiFieldBadge isAi={aiFields.actual_condition} isUserEdited={userEditedFields.actual_condition} />}
              >
                <TextInput
                  id="actual_condition"
                  value={form.actual_condition}
                  onChange={set("actual_condition")}
                  placeholder="e.g. 118.5°C"
                />
              </Field>
            </div>
          </div>

          {/* Section 4: Immediate Containment Action */}
          <div className="space-y-3">
            <SectionHeading>4. Immediate Containment</SectionHeading>
            <Field
              label="Immediate Action Taken"
              htmlFor="immediate_action"
              badge={<AiFieldBadge isAi={aiFields.immediate_action} isUserEdited={userEditedFields.immediate_action} />}
            >
              <TextArea
                id="immediate_action"
                rows={2}
                value={form.immediate_action}
                onChange={set("immediate_action")}
                placeholder="Immediate containment actions taken upon detection (e.g. cycle abort, load quarantined under tag Q-882)"
              />
            </Field>

            <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-2">
              <Field
                label="Batch Status"
                htmlFor="batch_status"
                badge={<AiFieldBadge isAi={aiFields.batch_status} isUserEdited={userEditedFields.batch_status} />}
              >
                <Select
                  id="batch_status"
                  value={form.batch_status}
                  onChange={set("batch_status")}
                  options={BATCH_STATUSES}
                  placeholder="Select batch status…"
                />
              </Field>

              <div className="flex h-10 items-center justify-between rounded-md border border-slate-200 px-3">
                <label htmlFor="qa_notified" className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                  <input
                    id="qa_notified"
                    type="checkbox"
                    checked={Boolean(form.qa_notified)}
                    onChange={set("qa_notified")}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-300"
                  />
                  <span>QA Notified upon detection</span>
                </label>
                <AiFieldBadge isAi={aiFields.qa_notified} isUserEdited={userEditedFields.qa_notified} />
              </div>
            </div>
          </div>

          {/* Section 5: Initial Quality Risk & Severity (User Overridable) */}
          <div className="space-y-3">
            <SectionHeading>5. Initial Risk & Severity Classification</SectionHeading>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Initial Impact"
                htmlFor="impact"
                badge={<AiFieldBadge isAi={aiFields.impact} isUserEdited={userEditedFields.impact} />}
              >
                <Select
                  id="impact"
                  value={form.impact}
                  onChange={set("impact")}
                  options={IMPACTS}
                  placeholder="Select impact area…"
                />
              </Field>

              <Field
                label="Initial Severity"
                htmlFor="severity"
                badge={<AiFieldBadge isAi={aiFields.severity} isUserEdited={userEditedFields.severity} />}
              >
                <Select
                  id="severity"
                  value={form.severity}
                  onChange={set("severity")}
                  options={SEVERITIES}
                  placeholder="Select severity level…"
                />
              </Field>
            </div>

            <Field
              label="Assessment Rationale"
              htmlFor="assessment_reason"
              badge={<AiFieldBadge isAi={aiFields.assessment_reason} isUserEdited={userEditedFields.assessment_reason} />}
            >
              <TextArea
                id="assessment_reason"
                rows={2}
                value={form.assessment_reason}
                onChange={set("assessment_reason")}
                placeholder="Rationale justifying the assigned severity and impact classification"
              />
            </Field>
          </div>
        </div>

        {/* Panel Footer: Save & Status */}
        <div className="space-y-3 border-t border-slate-200 px-5 py-4 bg-slate-50/50">
          {saveStatus === "succeeded" && lastSaved && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-xs text-emerald-800 flex items-center justify-between">
              <div>
                <span className="font-semibold">Deviation Saved:</span> Reference{" "}
                <span className="font-bold underline">{lastSaved.reference}</span> (Status:{" "}
                <span className="uppercase">{lastSaved.status}</span>). Form ready for next entry.
              </div>
              <span className="text-emerald-600 font-bold">✓</span>
            </div>
          )}

          {saveStatus === "failed" && saveError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              <p className="font-semibold">Could not save deviation:</p>
              <p>{saveError}</p>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-500">
              {!canSave && (
                <span className="text-amber-700">
                  Required to save: Title (3+ chars), Description (10+ chars), Type.
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setErrors({});
                  dispatch(resetForm());
                }}
                disabled={saving}
              >
                Reset
              </Button>

              <Button
                type="submit"
                disabled={saving || !canSave}
                className={!canSave ? "opacity-60 cursor-not-allowed" : ""}
                title={!canSave ? "Complete required fields (Title, Description, Type) to save" : "Save deviation to record"}
              >
                {saving ? "Saving…" : "Save Deviation"}
              </Button>
            </div>
          </div>
        </div>
      </form>
    </section>
  );
}
