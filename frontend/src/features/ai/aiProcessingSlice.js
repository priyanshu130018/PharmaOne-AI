import { createSlice } from "@reduxjs/toolkit";

export const STAGES = [
  { key: "ready", label: "Ready", desc: "Awaiting deviation input" },
  { key: "processing_document", label: "Processing document", desc: "Parsing document structure & OCR if scanned" },
  { key: "extracting_deviation", label: "Extracting deviation", desc: "Extracting structured deviation fields" },
  { key: "retrieving_references", label: "Retrieving references", desc: "Searching pharmaceutical SOPs & ICH guidelines" },
  { key: "assessing_impact", label: "Assessing impact", desc: "Evaluating quality risk & critical quality attributes" },
  { key: "assessing_severity", label: "Assessing severity", desc: "Evaluating initial severity classification per ICH Q9" },
  { key: "ready_for_review", label: "Ready for review", desc: "AI analysis complete — fields populated for human review" },
];

const initialState = {
  status: "idle", // "idle" | "loading" | "succeeded" | "failed"
  currentStage: "ready",
  stageMessage: "Ready to analyze deviation document or text.",
  extractedText: "",
  sourceType: "pdf",
  metadata: null,
  error: null,
};

const aiProcessingSlice = createSlice({
  name: "aiProcessing",
  initialState,
  reducers: {
    setStage(state, action) {
      const { stage, message } = action.payload;
      state.currentStage = stage;
      if (message) state.stageMessage = message;
      if (stage === "ready") state.status = "idle";
      else if (stage === "ready_for_review") state.status = "succeeded";
      else if (stage === "failed") state.status = "failed";
      else state.status = "loading";
    },
    setExtractedContent(state, action) {
      const { extracted_text, source_type, metadata } = action.payload;
      state.extractedText = extracted_text || "";
      state.sourceType = source_type || "pdf";
      state.metadata = metadata || null;
    },
    setProcessingError(state, action) {
      state.status = "failed";
      state.currentStage = "failed";
      state.error = action.payload;
      state.stageMessage = action.payload?.message || "Processing failed.";
    },
    resetProcessing(state) {
      return { ...initialState };
    },
  },
});

export const { setStage, setExtractedContent, setProcessingError, resetProcessing } =
  aiProcessingSlice.actions;
export default aiProcessingSlice.reducer;
