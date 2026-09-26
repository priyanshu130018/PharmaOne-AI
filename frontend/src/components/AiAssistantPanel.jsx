import React, { useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  processDeviationInput,
  setInputMode,
  setPastedText,
  setFileInfo,
  clearFile,
  clearAssistant,
  markApplied,
} from "../features/assistant/assistantSlice.js";
import { applySuggestions } from "../features/deviations/deviationsSlice.js";
import { Button, Badge } from "./ui.jsx";
import AssistantResult from "./AssistantResult.jsx";

const SAMPLE_TEXT = `Sterility test failure observed for morning batch LOT-2026-042 in Sterile Production.
Possible microbial contamination detected during testing of filled vials in Autoclave AC-02.
Product: SterileInjectable 100mL
Equipment: Autoclave AC-02
Department: Sterile Manufacturing
Chamber temperature dropped to 118.5°C during the 20-minute sterilization hold phase (approved range: 121.1°C +/- 0.5°C).
Immediate action: Cycle aborted, entire autoclave load placed on hold under tag Q-882 pending QA review. QA notified.`;

export const AIVOA_STAGES = [
  { key: "ready", label: "Ready", sub: "Awaiting input" },
  { key: "processing_document", label: "Processing document", sub: "Extracting text…" },
  { key: "extracting_deviation", label: "Extracting deviation", sub: "Structuring AIVOA fields" },
  { key: "retrieving_references", label: "Retrieving references", sub: "SOP vector search" },
  { key: "assessing_impact", label: "Assessing impact", sub: "CQAs & risk context" },
  { key: "assessing_severity", label: "Assessing severity", sub: "Quality-risk context" },
  { key: "ready_for_review", label: "Ready for review", sub: "Fields populated" },
];

function getStageIndex(currentStage) {
  const map = {
    ready: 0,
    uploading: 1,
    checking: 1,
    extracting: 1,
    processing_document: 1,
    extracting_deviation: 2,
    retrieving_references: 3,
    assessing_impact: 4,
    assessing_severity: 5,
    analyzing: 5,
    ready_for_review: 6,
    succeeded: 6,
  };
  return map[currentStage] ?? 0;
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export default function AiAssistantPanel() {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);
  const [selectedFileObj, setSelectedFileObj] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const {
    input,
    processing,
    extractedTextStatus,
    error,
    retry,
    currentProcessingSession,
    extraction,
    assessment,
    meta,
    applied,
  } = useSelector((s) => s.assistant);

  const loading = processing.status === "loading";
  const hasExtractedText = Boolean(extractedTextStatus?.extractedText);
  const hasResult = processing.status === "succeeded" && (extraction || assessment);

  const handleModeChange = (newMode) => {
    dispatch(setInputMode(newMode));
  };

  const handleFileSelect = (file) => {
    if (!file) return;
    setSelectedFileObj(file);
    dispatch(
      setFileInfo({
        name: file.name,
        size: file.size,
        type: file.type,
      })
    );
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleRemoveFile = () => {
    setSelectedFileObj(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    dispatch(clearFile());
  };

  const handleProcess = () => {
    if (input.mode === "upload") {
      if (!selectedFileObj) return;
      dispatch(
        processDeviationInput({
          file: selectedFileObj,
          mode: "upload",
          sourceType: "pdf",
        })
      );
    } else {
      if (!input.pastedText || input.pastedText.trim().length < 5) return;
      const isEmail = /From:\s*|Subject:\s*|To:\s*/i.test(input.pastedText);
      dispatch(
        processDeviationInput({
          text: input.pastedText,
          mode: "paste",
          sourceType: isEmail ? "email" : "text",
        })
      );
    }
  };

  const handleRetry = () => {
    if (retry.lastPayload) {
      dispatch(
        processDeviationInput({
          file: selectedFileObj || retry.lastPayload.file,
          text: retry.lastPayload.text || input.pastedText,
          sourceType: retry.lastPayload.sourceType || input.sourceType,
          mode: retry.lastPayload.mode || input.mode,
        })
      );
    } else {
      handleProcess();
    }
  };

  const handleClear = () => {
    setSelectedFileObj(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    dispatch(clearAssistant());
  };

  const handleApplyManually = () => {
    dispatch(
      applySuggestions({
        deviation: meta?.deviation,
        extraction,
        assessment,
        source: extractedTextStatus?.sourceType || input.sourceType || "text",
      })
    );
    dispatch(markApplied());
  };

  const canSubmit =
    !loading &&
    ((input.mode === "upload" && Boolean(selectedFileObj)) ||
      (input.mode === "paste" && input.pastedText.trim().length >= 5));

  const currentStageIdx = getStageIndex(processing.stage);

  return (
    <section
      aria-label="AI Deviation Assistant Panel"
      className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      {/* Header */}
      <header className="border-b border-slate-200 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-800">
                AI Deviation Assistant
              </h2>
              <span className="rounded-full bg-brand-50 border border-brand-200/80 px-2 py-0.5 text-[10px] font-semibold text-brand-700">
                AIVOA Workflow
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Primary intake channel: upload deviation PDF or paste text to auto-populate form.
            </p>
          </div>
          {currentProcessingSession?.sessionId && (
            <span className="text-[10px] text-slate-400 font-mono">
              {currentProcessingSession.sessionId.slice(-10)}
            </span>
          )}
        </div>

        {/* Mode Selector Tabs */}
        <div className="mt-3 flex rounded-lg bg-slate-100 p-1 text-xs font-medium">
          <button
            type="button"
            className={`flex-1 rounded-md py-1.5 transition ${
              input.mode === "upload"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
            onClick={() => handleModeChange("upload")}
            disabled={loading}
          >
            📄 Upload PDF / Document
          </button>
          <button
            type="button"
            className={`flex-1 rounded-md py-1.5 transition ${
              input.mode === "paste"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
            onClick={() => handleModeChange("paste")}
            disabled={loading}
          >
            📝 Paste Text / Email
          </button>
        </div>
      </header>

      {/* Main Body */}
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
        
        {/* Mode 1: Document Upload */}
        {input.mode === "upload" && (
          <div className="space-y-3">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.txt,.log,.eml"
              className="hidden"
              id="pdf-upload-input"
            />

            {!selectedFileObj ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition ${
                  isDragOver
                    ? "border-brand-500 bg-brand-50/50"
                    : "border-slate-300 hover:border-brand-400 hover:bg-slate-50"
                }`}
              >
                <div className="mb-2 rounded-full bg-slate-100 p-3 text-slate-600">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                </div>
                <p className="text-xs font-semibold text-slate-700">
                  Drop deviation PDF, scanned report, or document here
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Supports PDF (digital or scanned with OCR), TXT, EML up to 10MB
                </p>
                <span className="mt-3 inline-block rounded bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
                  Browse Files
                </span>
              </div>
            ) : (
              <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-center gap-3 truncate">
                  <div className="rounded bg-brand-100 p-2 text-brand-700">
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>
                  <div className="truncate">
                    <p className="truncate text-xs font-medium text-slate-800">
                      {selectedFileObj.name}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      {formatBytes(selectedFileObj.size)}
                    </p>
                  </div>
                </div>
                {!loading && (
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
                    title="Remove file"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Mode 2: Paste Text / Email */}
        {input.mode === "paste" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label
                htmlFor="pasted-content"
                className="text-xs font-semibold uppercase tracking-wide text-slate-500"
              >
                Deviation Content (Report, Email, Shift Log)
              </label>
              <button
                type="button"
                className="text-xs font-medium text-brand-600 hover:text-brand-700"
                onClick={() => dispatch(setPastedText(SAMPLE_TEXT))}
                disabled={loading}
              >
                Load example
              </button>
            </div>
            <textarea
              id="pasted-content"
              rows={7}
              value={input.pastedText}
              onChange={(e) => dispatch(setPastedText(e.target.value))}
              placeholder="Paste deviation description, shift log, or notification email body here… (min 5 characters)"
              className="field-input resize-y font-mono text-xs leading-relaxed"
              disabled={loading}
            />
            <div className="flex justify-end text-xs text-slate-400">
              {input.pastedText.length} characters
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-3 pt-1">
          <Button
            type="button"
            onClick={handleProcess}
            disabled={!canSubmit}
            className="flex-1 sm:flex-initial"
          >
            {loading ? "Processing…" : input.mode === "upload" ? "Analyze Document" : "Analyze Text"}
          </Button>

          {(hasResult || hasExtractedText || error || selectedFileObj || input.pastedText) && (
            <Button
              type="button"
              variant="ghost"
              onClick={handleClear}
              disabled={loading}
            >
              Clear
            </Button>
          )}
        </div>

        {/* Real Processing Stage Progression Stepper (No fake percentages) */}
        {loading && (
          <div className="rounded-lg border border-brand-200 bg-brand-50/50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <svg
                className="h-4 w-4 animate-spin text-brand-600 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
              <span className="text-xs font-semibold text-brand-900">
                {processing.stageMessage || "Processing document: Extracting text…"}
              </span>
            </div>

            {/* Stage Progression Cards */}
            <div className="grid grid-cols-2 gap-1.5 text-xs sm:grid-cols-3 md:grid-cols-4">
              {AIVOA_STAGES.filter((s) => s.key !== "ready").map((stg, idx) => {
                const stageIdxInList = idx + 1;
                const isActive = stageIdxInList === currentStageIdx;
                const isPassed = currentStageIdx > stageIdxInList;

                return (
                  <div
                    key={stg.key}
                    className={`rounded border p-2 transition text-left ${
                      isActive
                        ? "border-brand-500 bg-white text-brand-700 font-semibold shadow-xs"
                        : isPassed
                        ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                        : "border-slate-200 bg-slate-50 text-slate-400"
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      {isPassed ? (
                        <span className="font-bold text-emerald-600">✓</span>
                      ) : isActive ? (
                        <span className="h-1.5 w-1.5 rounded-full bg-brand-600 animate-pulse shrink-0" />
                      ) : (
                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 shrink-0" />
                      )}
                      <span className="truncate text-[11px]">{stg.label}</span>
                    </div>
                    <p className="text-[10px] mt-0.5 truncate text-slate-500 font-normal">
                      {stg.sub}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error State with Structured Message & One-Click Retry */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-2">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2 text-red-800 font-semibold text-sm">
                <svg
                  className="h-4 w-4 shrink-0 text-red-600"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{typeof error === "object" && error.title ? error.title : "Processing Error"}</span>
              </div>
              {retry.canRetry && (
                <button
                  type="button"
                  onClick={handleRetry}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-red-700 hover:text-red-900 underline"
                >
                  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Retry ({retry.retryCount})
                </button>
              )}
            </div>

            <p className="text-xs text-red-700">
              {typeof error === "object" ? error.message : error}
            </p>

            {(typeof error === "object" ? error.message : error).toLowerCase().includes("ocr") && (
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => dispatch(setInputMode("paste"))}
                  className="text-xs font-medium text-red-800 underline hover:text-red-900"
                >
                  Switch to paste text directly →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Extracted Content & Auto-Population Success Banner */}
        {hasExtractedText && (
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                Extracted Document Content
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {extractedTextStatus.sourceType && (
                  <Badge className="border-slate-300 bg-white text-slate-700">
                    Source: {extractedTextStatus.sourceType.toUpperCase()}
                  </Badge>
                )}
                {extractedTextStatus.metadata?.page_count > 0 && (
                  <Badge className="border-slate-300 bg-white text-slate-700">
                    Pages: {extractedTextStatus.metadata.page_count}
                  </Badge>
                )}
                {extractedTextStatus.metadata?.character_count > 0 && (
                  <Badge className="border-slate-300 bg-white text-slate-700">
                    Chars: {extractedTextStatus.metadata.character_count}
                  </Badge>
                )}
                {extractedTextStatus.metadata?.ocr_applied && (
                  <Badge className="border-amber-200 bg-amber-50 text-amber-700">
                    OCR Fallback Applied
                  </Badge>
                )}
              </div>
            </div>

            <div className="max-h-36 overflow-y-auto rounded border border-slate-200 bg-white p-2.5 text-xs text-slate-700 font-mono whitespace-pre-wrap leading-relaxed">
              {extractedTextStatus.extractedText}
            </div>

            {/* Indication of automated population into the left form */}
            <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium pt-1">
              <svg className="h-4 w-4 shrink-0 text-emerald-600" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span>Extracted fields automatically populated into deviation form on the left.</span>
            </div>
          </div>
        )}

        {/* Structured AI Analysis Results */}
        {hasResult && (
          <AssistantResult
            extraction={extraction}
            assessment={assessment}
            meta={meta}
            applied={applied}
            onApply={handleApplyManually}
          />
        )}
      </div>
    </section>
  );
}
