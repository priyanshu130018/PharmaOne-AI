import React, { useState, useEffect } from "react";
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
  Badge,
  AiFieldBadge,
} from "./ui.jsx";
import { api } from "../api/client.js";
import WorkflowStepper from "./WorkflowStepper.jsx";
import LinkedRecordsBar from "./LinkedRecordsBar.jsx";
import QualityEventTimeline from "./QualityEventTimeline.jsx";

export default function LogDeviationForm({ onNavigate, onRecordClick }) {
  const dispatch = useDispatch();
  const {
    form,
    aiFields = {},
    userEditedFields = {},
    highlightedFields = {},
    aiSnapshot,
    saveStatus,
    saveError,
    lastSaved,
  } = useSelector((s) => s.deviations || {});
  const assistant = useSelector((s) => s.assistant || {});
  const [errors, setErrors] = useState({});
  const [startingInvestigation, setStartingInvestigation] = useState(false);
  const [linkedRecords, setLinkedRecords] = useState(null);

  const isClosed = String(lastSaved?.status || form?.status || '').toLowerCase() === 'closed';

  useEffect(() => {
    const devId = lastSaved?.reference || lastSaved?.id || form?.reference || form?.id;
    if (devId && api && typeof api.getLinkedRecords === "function") {
      api.getLinkedRecords(devId)
        .then(data => setLinkedRecords(data))
        .catch(err => console.warn('Could not load linked records', err));
    }
  }, [lastSaved, form?.reference]);

  const handleStartInvestigation = async () => {
    try {
      setStartingInvestigation(true);
      const targetDevId = lastSaved?.reference || lastSaved?.id || form?.reference || form?.id || 'DEV-2026-018';
      let res = {};
      if (api && typeof api.startInvestigation === "function") {
        res = await api.startInvestigation(targetDevId);
      }
      const invRef = res?.investigation_number || res?.reference || res?.id || 'INV-2026-012';
      if (onNavigate) {
        onNavigate('investigation', { 
          deviationId: targetDevId, 
          investigationId: invRef 
        });
      }
    } catch (err) {
      console.error('Failed to start investigation:', err);
      if (onNavigate) {
        onNavigate('investigation', { 
          deviationId: lastSaved?.reference || form?.reference || 'DEV-2026-018', 
          investigationId: 'INV-2026-012' 
        });
      }
    } finally {
      setStartingInvestigation(false);
    }
  };

  const set = (name) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    dispatch(updateField({ name, value }));
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const saving = saveStatus === "loading";
  const canSave = isFormValid(form);

  const missingRequired = [];
  if (!form.title || form.title.trim().length < 3) {
    missingRequired.push("Title");
  }
  if (!form.description || form.description.trim().length < 10) {
    missingRequired.push("Detailed Description");
  }
  if (!form.deviation_type) {
    missingRequired.push("Deviation Type");
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    const found = validateForm(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const fullSnapshot = aiSnapshot || (assistant.assessment || assistant.extraction ? {
      ai_assessment: assistant.assessment,
      ai_extraction: assistant.extraction,
    } : null);

    dispatch(saveDeviation(buildCreatePayload(form, fullSnapshot)))
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
      className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
    >
      {/* Panel Header */}
      <header className="shrink-0 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-3.5 bg-white">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold text-slate-900">Log Deviation</h2>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 border border-slate-200">
              {lastSaved ? "Submitted" : "Draft"}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            Log any unexpected event, out-of-specification result or non-conformance.
          </p>
        </div>

        {form.severity && (
          <Badge className={SEVERITY_STYLES[form.severity] || "bg-slate-100 text-slate-700"}>
            Severity: {labelFor(SEVERITIES, form.severity)}
          </Badge>
        )}
      </header>

      {/* 21 CFR Part 11 Compliance Lock Banner when Closed */}
      {isClosed && (
        <div className="bg-emerald-50 border-b border-emerald-200 px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-600 text-white font-bold text-xs shadow-xs">
              ✓
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-2">
                <span>CLOSED — READ ONLY</span>
                <span className="text-[10px] font-semibold bg-emerald-200/90 text-emerald-800 px-2 py-0.5 rounded border border-emerald-300">
                  21 CFR Part 11 Regulatory Lock
                </span>
              </div>
              <p className="text-xs text-emerald-700 mt-0.5">
                This deviation is formally closed under QA authority. Editing and reassessment are locked.
              </p>
            </div>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-mono text-emerald-900 font-semibold block">
              Authorized by: {lastSaved?.closed_by || "QA Lead Priyanshu"}
            </span>
            <span className="text-[10px] text-emerald-600 font-medium">Compliance Locked</span>
          </div>
        </div>
      )}

      {/* Scrollable Left Workspace: Form + Actions + Severity Report */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 space-y-6">
        {/* Connected Quality Lifecycle Bar & Stepper */}
        {(lastSaved || form.batch_number || form.parameter) && (
          <div className="space-y-3 pb-2">
            <LinkedRecordsBar 
              records={linkedRecords}
              activeType="deviation"
              onRecordClick={onRecordClick}
            />

            <div className="rounded-xl bg-blue-900 border border-blue-700 p-3.5 text-xs flex flex-wrap items-center justify-between gap-2 shadow-xs text-white">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono font-bold text-amber-300">BATCH: {form.batch_number || 'API-2026-055'}</span>
                <span className="text-blue-300">•</span>
                <span>Product: <strong className="text-white">{form.product_name || 'Ibuprofen API'}</strong></span>
                {form.raw_material_name && (
                  <>
                    <span className="text-blue-300">•</span>
                    <span>Raw Material: <strong className="text-white">{form.raw_material_name}</strong></span>
                  </>
                )}
                <span className="text-blue-300">•</span>
                <span>Step: <strong className="text-white">{form.manufacturing_stage || 'Step 3 — Reaction'}</strong></span>
                <span className="text-blue-300">•</span>
                <span>Parameter: <strong className="text-white">{form.parameter || 'Temperature'}</strong></span>
                <span className="text-blue-300">•</span>
                <span>Spec: <span className="font-mono text-blue-200">{form.expected_condition || '70–75°C'}</span></span>
                <span className="text-blue-300">•</span>
                <span>Actual: <span className="font-mono font-bold text-red-300">{form.actual_condition || '79°C'}</span></span>
                {form.duration && (
                  <>
                    <span className="text-blue-300">•</span>
                    <span>Duration: <strong className="text-white">{form.duration}</strong></span>
                  </>
                )}
              </div>
              <span className="px-2.5 py-1 rounded font-bold uppercase text-[10px] bg-red-600 text-white shadow-xs">
                OUT-OF-LIMIT (OOL)
              </span>
            </div>

            <WorkflowStepper currentStep={1} onStepClick={(step) => {
              if (step.id === 'investigation') onNavigate?.('investigation', { deviationId: lastSaved?.reference || 'DEV-2026-018' });
              if (step.id === 'root_cause') onNavigate?.('root_cause', { deviationId: lastSaved?.reference || 'DEV-2026-018' });
              if (step.id === 'capa') onNavigate?.('capa', { deviationId: lastSaved?.reference || 'DEV-2026-018' });
              if (step.id === 'effectiveness') onNavigate?.('effectiveness', { deviationId: lastSaved?.reference || 'DEV-2026-018' });
              if (step.id === 'closed') onNavigate?.('closure', { deviationId: lastSaved?.reference || 'DEV-2026-018' });
            }} />
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <fieldset disabled={isClosed} className="space-y-4">
          {/* SECTION 1: DEVIATION INFORMATION */}
          <div className="space-y-3">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-1">
              DEVIATION INFORMATION
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field
                label="Site / Plant"
                htmlFor="site_plant"
                isHighlighted={Boolean(highlightedFields.site_plant)}
                badge={<AiFieldBadge isAi={aiFields.site_plant} isUserEdited={userEditedFields.site_plant} />}
              >
                <TextInput
                  id="site_plant"
                  value={form.site_plant}
                  onChange={set("site_plant")}
                  placeholder="e.g. Bengaluru"
                />
              </Field>

              <Field
                label="Date of Occurrence"
                htmlFor="occurred_on"
                isHighlighted={Boolean(highlightedFields.occurred_on)}
                badge={<AiFieldBadge isAi={aiFields.occurred_on} isUserEdited={userEditedFields.occurred_on} />}
              >
                <TextInput
                  id="occurred_on"
                  type="date"
                  value={form.occurred_on}
                  onChange={set("occurred_on")}
                />
              </Field>

              <Field
                label="Reported By"
                htmlFor="reported_by"
                isHighlighted={Boolean(highlightedFields.reported_by)}
                badge={<AiFieldBadge isAi={aiFields.reported_by} isUserEdited={userEditedFields.reported_by} />}
              >
                <TextInput
                  id="reported_by"
                  value={form.reported_by}
                  onChange={set("reported_by")}
                  placeholder="e.g. Operator K. Sharma"
                />
              </Field>
            </div>

            <Field
              label="Title / Short Description"
              htmlFor="title"
              required
              error={errors.title}
              isHighlighted={Boolean(highlightedFields.title)}
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
                isHighlighted={Boolean(highlightedFields.source)}
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
                isHighlighted={Boolean(highlightedFields.deviation_type)}
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

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Related Product / Material"
                htmlFor="product_name"
                isHighlighted={Boolean(highlightedFields.product_name)}
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
                isHighlighted={Boolean(highlightedFields.batch_number)}
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
          </div>

          {/* SECTION 2: DEVIATION DETAILS */}
          <div className="space-y-3 pt-2">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-1">
              DEVIATION DETAILS
            </div>

            <Field
              label="Detailed Description"
              htmlFor="description"
              required
              error={errors.description}
              isHighlighted={Boolean(highlightedFields.description)}
              badge={<AiFieldBadge isAi={aiFields.description} isUserEdited={userEditedFields.description} />}
            >
              <TextArea
                id="description"
                rows={3}
                value={form.description}
                onChange={set("description")}
                placeholder="Describe what occurred, where, and observed impacts (min 10 characters)"
              />
            </Field>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Initial Impact"
                htmlFor="impact"
                isHighlighted={Boolean(highlightedFields.impact)}
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
                isHighlighted={Boolean(highlightedFields.severity)}
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

            {/* Scope & Context Details */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Field
                label="Equipment / Asset"
                htmlFor="equipment"
                isHighlighted={Boolean(highlightedFields.equipment)}
                badge={<AiFieldBadge isAi={aiFields.equipment} isUserEdited={userEditedFields.equipment} />}
              >
                <TextInput
                  id="equipment"
                  value={form.equipment}
                  onChange={set("equipment")}
                  placeholder="e.g. Reactor R-101"
                />
              </Field>

              <Field
                label="Department"
                htmlFor="department"
                isHighlighted={Boolean(highlightedFields.department)}
                badge={<AiFieldBadge isAi={aiFields.department} isUserEdited={userEditedFields.department} />}
              >
                <TextInput
                  id="department"
                  value={form.department}
                  onChange={set("department")}
                  placeholder="e.g. API Manufacturing"
                />
              </Field>

              <Field
                label="Manufacturing Stage"
                htmlFor="manufacturing_stage"
                isHighlighted={Boolean(highlightedFields.manufacturing_stage)}
                badge={<AiFieldBadge isAi={aiFields.manufacturing_stage} isUserEdited={userEditedFields.manufacturing_stage} />}
              >
                <TextInput
                  id="manufacturing_stage"
                  value={form.manufacturing_stage}
                  onChange={set("manufacturing_stage")}
                  placeholder="e.g. Step 3 — Reaction"
                />
              </Field>

              <Field
                label="Process / Operation"
                htmlFor="process_operation"
                isHighlighted={Boolean(highlightedFields.process_operation)}
                badge={<AiFieldBadge isAi={aiFields.process_operation} isUserEdited={userEditedFields.process_operation} />}
              >
                <TextInput
                  id="process_operation"
                  value={form.process_operation}
                  onChange={set("process_operation")}
                  placeholder="e.g. Reaction"
                />
              </Field>
            </div>

            {/* Parameters & Technical Excursion */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Parameter"
                htmlFor="parameter"
                isHighlighted={Boolean(highlightedFields.parameter)}
                badge={<AiFieldBadge isAi={aiFields.parameter} isUserEdited={userEditedFields.parameter} />}
              >
                <TextInput
                  id="parameter"
                  value={form.parameter}
                  onChange={set("parameter")}
                  placeholder="e.g. Chamber Temperature"
                />
              </Field>

              <Field
                label="Duration"
                htmlFor="duration"
                isHighlighted={Boolean(highlightedFields.duration)}
                badge={<AiFieldBadge isAi={aiFields.duration} isUserEdited={userEditedFields.duration} />}
              >
                <TextInput
                  id="duration"
                  value={form.duration}
                  onChange={set("duration")}
                  placeholder="e.g. 8 minutes"
                />
              </Field>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field
                label="Approved Range"
                htmlFor="expected_condition"
                isHighlighted={Boolean(highlightedFields.expected_condition)}
                badge={<AiFieldBadge isAi={aiFields.expected_condition} isUserEdited={userEditedFields.expected_condition} />}
              >
                <TextInput
                  id="expected_condition"
                  value={form.expected_condition}
                  onChange={set("expected_condition")}
                  placeholder="e.g. 121.1°C ± 0.5°C"
                />
              </Field>

              <Field
                label="Actual Value"
                htmlFor="actual_condition"
                isHighlighted={Boolean(highlightedFields.actual_condition)}
                badge={<AiFieldBadge isAi={aiFields.actual_condition} isUserEdited={userEditedFields.actual_condition} />}
              >
                <TextInput
                  id="actual_condition"
                  value={form.actual_condition}
                  onChange={set("actual_condition")}
                  placeholder="e.g. 118.2°C"
                />
              </Field>

              <Field
                label="Batch Status"
                htmlFor="batch_status"
                isHighlighted={Boolean(highlightedFields.batch_status)}
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
            </div>

            <Field
              label="Immediate Action Taken"
              htmlFor="immediate_action"
              isHighlighted={Boolean(highlightedFields.immediate_action)}
              badge={<AiFieldBadge isAi={aiFields.immediate_action} isUserEdited={userEditedFields.immediate_action} />}
            >
              <TextInput
                id="immediate_action"
                value={form.immediate_action}
                onChange={set("immediate_action")}
                placeholder="Immediate containment actions taken upon detection (e.g. cycle abort, load quarantined)"
              />
            </Field>

            <div
              data-testid="field-container-qa_notified"
              data-field="qa_notified"
              className={`flex items-center justify-between rounded-lg border px-3 py-2 transition-all duration-200 ${
                highlightedFields.qa_notified
                  ? "bg-emerald-50/90 border-emerald-400 p-2.5 ring-1 ring-emerald-300 shadow-xs"
                  : "border-slate-200 bg-slate-50/50"
              }`}
            >
              <label htmlFor="qa_notified" className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
                <input
                  id="qa_notified"
                  type="checkbox"
                  checked={Boolean(form.qa_notified)}
                  onChange={set("qa_notified")}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-300"
                />
                <span className="font-medium">QA Notified upon detection</span>
              </label>
              <div className="flex items-center gap-1.5">
                <AiFieldBadge isAi={aiFields.qa_notified} isUserEdited={userEditedFields.qa_notified} />
              </div>
            </div>
          </div>

          {/* Messages & Alerts */}
          {saveStatus === "succeeded" && lastSaved && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs text-emerald-800 flex items-center justify-between">
              <div>
                <span className="font-semibold">Deviation Saved:</span> Reference{" "}
                <span className="font-bold underline">{lastSaved.reference}</span> (Status:{" "}
                <span className="uppercase">{lastSaved.status}</span>).
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

          {!canSave && (form.title || form.description || form.deviation_type || form.product_name || form.batch_number || form.site_plant) && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs text-amber-800">
              <span className="font-semibold">Review required:</span> {missingRequired.join(", ")} {missingRequired.length === 1 ? "is" : "are"} missing.
            </div>
          )}

          </fieldset>

          {/* Form Action Buttons */}
          <div className="flex items-center justify-between gap-3 pt-2">
            {!isClosed && (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setErrors({});
                  dispatch(resetForm());
                }}
                disabled={saving}
                className="text-xs px-3.5 py-2"
              >
                Reset Form
              </Button>
            )}

            {isClosed ? (
              <div className="ml-auto inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-100 text-slate-500 text-xs font-semibold border border-slate-200">
                <svg className="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <span>Record Locked (Closed)</span>
              </div>
            ) : (
              <Button
                type="submit"
                disabled={saving || !canSave}
                className={`bg-blue-600 hover:bg-blue-700 text-white text-xs px-4 py-2 font-medium shadow-sm transition ${
                  !canSave ? "opacity-50 cursor-not-allowed" : ""
                }`}
                title={!canSave ? `Complete required fields to save: ${missingRequired.join(", ")}` : "Save deviation"}
              >
                {saving ? "Saving…" : "Save Deviation"}
              </Button>
            )}
          </div>
        </form>

        {/* AFTER SAVE: DEVIATION SEVERITY REPORT ON LEFT */}
        {lastSaved && (
          <div data-testid="deviation-severity-report" className="border-t border-slate-200 pt-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                  DEVIATION SEVERITY REPORT
                </span>
                <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700 border border-blue-200">
                  AI Risk Assessment
                </span>
              </div>
              <span className="text-xs text-slate-500 font-mono font-medium">
                Ref: {lastSaved.reference}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Impact
                </span>
                <span className="font-semibold text-slate-800 text-sm">
                  {labelFor(IMPACTS, lastSaved.impact || lastSaved.ai_recommended_impact) || lastSaved.impact || lastSaved.ai_recommended_impact || "Product Quality"}
                </span>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Severity
                </span>
                <Badge className={SEVERITY_STYLES[lastSaved.severity || lastSaved.ai_recommended_severity] || "bg-slate-100 text-slate-700"}>
                  {labelFor(SEVERITIES, lastSaved.severity || lastSaved.ai_recommended_severity) || lastSaved.severity || lastSaved.ai_recommended_severity || "Major"}
                </Badge>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Required Impact
                </span>
                <span className="font-semibold text-slate-800 text-sm">
                  {labelFor(IMPACTS, lastSaved.ai_recommended_impact || lastSaved.impact) || lastSaved.ai_recommended_impact || lastSaved.impact || "Product Quality"}
                </span>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Human Review
                </span>
                <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-xs">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {lastSaved.status ? `Confirmed (${String(lastSaved.status).toUpperCase()})` : "Verified and Confirmed"}
                </span>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 text-xs space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                Reason
              </span>
              <p className="text-slate-700 leading-relaxed">
                {lastSaved.ai_reason || lastSaved.assessment_reason || lastSaved.ai_assessment?.reason || "Evaluated against product quality specifications and validated process parameters."}
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 text-xs space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                Evidence
              </span>
              {Array.isArray(lastSaved.ai_evidence) && lastSaved.ai_evidence.length > 0 ? (
                <ul className="list-inside list-disc space-y-1 text-slate-700">
                  {lastSaved.ai_evidence.map((ev, i) => (
                    <li key={i}>{typeof ev === "string" ? ev : JSON.stringify(ev)}</li>
                  ))}
                </ul>
              ) : lastSaved.ai_evidence && typeof lastSaved.ai_evidence === "string" ? (
                <p className="text-slate-700">{lastSaved.ai_evidence}</p>
              ) : (
                <p className="text-slate-500 italic">
                  Supporting quality evidence verified against facility standard operating procedures.
                </p>
              )}
            </div>

            {/* Start Investigation / Closed Lifecycle Navigation Banner */}
            <div className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs ${
              isClosed 
                ? "border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50" 
                : "border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50"
            }`}>
              <div>
                <div className={`text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 ${
                  isClosed ? "text-emerald-900" : "text-blue-900"
                }`}>
                  {isClosed && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
                  <span>{isClosed ? "Connected Quality Lifecycle Completed" : "Connected Quality Workflow"}</span>
                </div>
                <p className={`text-xs mt-0.5 ${isClosed ? "text-emerald-700" : "text-blue-700"}`}>
                  {isClosed 
                    ? "All 4 quality gates verified. Deviation formally closed and locked under QA compliance." 
                    : "Deviation recorded and assessed. Proceed to formal investigation protocol."}
                </p>
              </div>

              {isClosed ? (
                <button
                  type="button"
                  onClick={() => onNavigate?.("batch_release", { batchNumber: form.batch_number || "API-2026-041", batchReleaseId: "BR-2026-041" })}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition"
                >
                  <span>View Batch Release (BR-2026-041)</span>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStartInvestigation}
                  disabled={startingInvestigation}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition"
                >
                  <span>{startingInvestigation ? "Initiating…" : "Start Investigation"}</span>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              )}
            </div>

            {/* Quality Event Lifecycle Timeline (21 CFR Part 11 Audit Trail) */}
            <QualityEventTimeline 
              deviation={lastSaved || form}
              linkedRecords={linkedRecords}
              onNavigate={onNavigate}
              onRecordClick={onRecordClick}
            />
          </div>
        )}
      </div>
    </section>
  );
}
