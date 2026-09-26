import React from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  processContent,
  setRawContent,
  markApplied,
  clearAssistant,
} from "../features/assistant/assistantSlice.js";
import { applySuggestions } from "../features/deviations/deviationsSlice.js";
import { Button } from "./ui.jsx";
import AssistantResult from "./AssistantResult.jsx";

const SAMPLE = `Sterility test failure observed for the morning batch. Possible microbial
contamination detected during testing of the filled vials.
Product: SterileInjectable
Batch: B-2026-042
The affected units were placed on hold pending QA review.`;

export default function AiAssistantPanel() {
  const dispatch = useDispatch();
  const { rawContent, status, error, extraction, assessment, meta, applied } =
    useSelector((s) => s.assistant);

  const loading = status === "loading";
  const hasResult = status === "succeeded" && (extraction || assessment);

  const onProcess = () => {
    if (rawContent.trim().length < 5) return;
    dispatch(processContent({ content: rawContent, source: "text" }));
  };

  const onApply = () => {
    dispatch(applySuggestions({ extraction, assessment }));
    dispatch(markApplied());
  };

  return (
    <section className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-slate-800">AI Deviation Assistant</h2>
          <p className="text-xs text-slate-500">
            Paste a report or email. The assistant extracts fields and suggests a risk
            classification for your review.
          </p>
        </div>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="raw" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Deviation content
            </label>
            <button
              type="button"
              className="text-xs font-medium text-brand-600 hover:text-brand-700"
              onClick={() => dispatch(setRawContent(SAMPLE))}
            >
              Load example
            </button>
          </div>
          <textarea
            id="raw"
            rows={7}
            value={rawContent}
            onChange={(e) => dispatch(setRawContent(e.target.value))}
            placeholder="Paste the deviation description, report, or email body here…"
            className="field-input resize-y"
          />
        </div>

        <div className="flex items-center gap-3">
          <Button type="button" onClick={onProcess} disabled={loading || rawContent.trim().length < 5}>
            {loading ? "Processing…" : "Process with AI"}
          </Button>
          {(hasResult || error) && (
            <Button type="button" variant="ghost" onClick={() => dispatch(clearAssistant())}>
              Clear
            </Button>
          )}
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {hasResult && (
          <AssistantResult
            extraction={extraction}
            assessment={assessment}
            meta={meta}
            applied={applied}
            onApply={onApply}
          />
        )}
      </div>
    </section>
  );
}
