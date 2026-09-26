import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";
import { applySuggestions } from "../deviations/deviationsSlice.js";
import { setAssessment } from "../assessment/assessmentSlice.js";
import { setStage, setExtractedContent, setProcessingError } from "../ai/aiProcessingSlice.js";

// Helper for user-friendly error formatting
export function formatHumanReadableError(err) {
  const rawMsg = typeof err === "string" ? err : err?.message || "";
  const lower = rawMsg.toLowerCase();

  if (lower.includes("ocr") && (lower.includes("unavailable") || lower.includes("failed"))) {
    return {
      title: "Processing Error",
      message: "The document appears to be a scanned image and OCR is unavailable. Please upload a digital PDF or paste the text directly.",
      code: "OCR_UNAVAILABLE",
    };
  }

  if (lower.includes("unsupported") || lower.includes("file type")) {
    return {
      title: "Processing Error",
      message: "Unsupported file type. Please upload a standard PDF, TXT, or email document.",
      code: "UNSUPPORTED_FILE_TYPE",
    };
  }

  if (lower.includes("oversized") || lower.includes("exceeds")) {
    return {
      title: "Processing Error",
      message: "The uploaded file exceeds the 10MB limit. Please provide a smaller document.",
      code: "FILE_OVERSIZED",
    };
  }

  if (lower.includes("timeout") || lower.includes("network")) {
    return {
      title: "Processing Error",
      message: rawMsg || "Network timeout during upload. Please check your connection and retry.",
      code: "NETWORK_TIMEOUT",
    };
  }

  return {
    title: "Processing Error",
    message: rawMsg || "An error occurred during deviation processing. Please check the content and retry.",
    code: "PROCESS_ERROR",
  };
}

// Multi-stage deviation extraction and AI analysis pipeline
export const processDeviationInput = createAsyncThunk(
  "assistant/processInput",
  async ({ file, text, sourceType = "text", mode = "paste" }, { dispatch, rejectWithValue }) => {
    const sessionId = "session-" + Date.now();
    try {
      let extractionRes;

      if (mode === "upload" && file) {
        // Stage 1: Processing document
        dispatch(
          setProcessingStage({
            stage: "processing_document",
            message: "Processing document: Extracting text…",
            sessionId,
          })
        );
        dispatch(
          setStage({
            stage: "processing_document",
            message: "Processing document: Extracting text…",
          })
        );

        extractionRes = await api.extractDocument(file);
      } else {
        // Stage: Extracting deviation
        dispatch(
          setProcessingStage({
            stage: "extracting_deviation",
            message: "Extracting text and normalizing deviation content…",
            sessionId,
          })
        );
        dispatch(
          setStage({
            stage: "extracting_deviation",
            message: "Extracting text and normalizing deviation content…",
          })
        );

        extractionRes = await api.extractText(text, sourceType);
      }

      if (!extractionRes || !extractionRes.success) {
        const errorMsg =
          extractionRes?.error?.message ||
          "Could not extract usable text from the provided document.";
        const formatted = formatHumanReadableError(errorMsg);
        dispatch(setProcessingError(formatted));
        return rejectWithValue({
          message: formatted.message,
          title: formatted.title,
          code: extractionRes?.error?.code || formatted.code,
          stage: "extracting",
          sessionId,
        });
      }

      dispatch(setExtractedResult(extractionRes));
      dispatch(setExtractedContent(extractionRes));

      // Stage: Retrieving references
      dispatch(
        setProcessingStage({
          stage: "retrieving_references",
          message: "Retrieving references from pharmaceutical SOPs…",
          sessionId,
        })
      );
      dispatch(
        setStage({
          stage: "retrieving_references",
          message: "Retrieving references from pharmaceutical SOPs…",
        })
      );

      // Stage: Assessing impact
      dispatch(
        setProcessingStage({
          stage: "assessing_impact",
          message: "Assessing impact on quality, CQAs, and patient safety…",
          sessionId,
        })
      );
      dispatch(
        setStage({
          stage: "assessing_impact",
          message: "Assessing impact on quality, CQAs, and patient safety…",
        })
      );

      const aiRes = await api.processDeviation(
        extractionRes.extracted_text,
        extractionRes.source_type || sourceType
      );

      // Stage: Assessing severity
      dispatch(
        setProcessingStage({
          stage: "assessing_severity",
          message: "Assessing initial severity recommendation based on quality-risk context…",
          sessionId,
        })
      );
      dispatch(
        setStage({
          stage: "assessing_severity",
          message: "Assessing initial severity recommendation based on quality-risk context…",
        })
      );

      // Automatically populate the left-hand form with extracted fields
      if (aiRes?.deviation || aiRes?.extraction || aiRes?.assessment) {
        dispatch(
          applySuggestions({
            deviation: aiRes.deviation,
            extraction: aiRes.extraction,
            assessment: aiRes.assessment,
            source: extractionRes.source_type || sourceType,
          })
        );
      }

      // Update dedicated assessment slice
      if (aiRes) {
        dispatch(setAssessment(aiRes));
      }

      // Final stage: Ready for review
      dispatch(
        setProcessingStage({
          stage: "ready_for_review",
          message: "Ready for review: Extracted fields automatically populated into deviation form.",
          sessionId,
        })
      );
      dispatch(
        setStage({
          stage: "ready_for_review",
          message: "Ready for review: Extracted fields automatically populated into deviation form.",
        })
      );

      return {
        extractionRes,
        aiRes,
        sessionId,
      };
    } catch (err) {
      const formatted = formatHumanReadableError(err);
      dispatch(setProcessingError(formatted));
      return rejectWithValue({
        message: formatted.message,
        title: formatted.title,
        code: formatted.code,
        stage: "processing",
        sessionId,
      });
    }
  }
);

// Backward-compatible thunk for existing callers
export const processContent = createAsyncThunk(
  "assistant/process",
  async ({ content, source = "text" }, { dispatch }) => {
    return dispatch(
      processDeviationInput({
        text: content,
        sourceType: source,
        mode: "paste",
      })
    ).unwrap();
  }
);

const initialInputState = {
  mode: "upload", // "upload" | "paste"
  pastedText: "",
  sourceType: "pdf", // "pdf" | "text" | "email"
  fileInfo: null, // { name, size, type }
};

const initialProcessingState = {
  status: "idle", // "idle" | "loading" | "succeeded" | "failed"
  stage: "ready", // "ready" | "processing_document" | "extracting_deviation" | "retrieving_references" | "assessing_impact" | "assessing_severity" | "ready_for_review"
  stageMessage: "",
};

const initialExtractedTextStatus = {
  success: false,
  extractedText: "",
  sourceType: "pdf",
  metadata: null,
};

const initialSessionState = {
  sessionId: null,
  startedAt: null,
  completedAt: null,
};

const initialRetryState = {
  canRetry: false,
  retryCount: 0,
  lastPayload: null,
};

const initialState = {
  input: { ...initialInputState },
  processing: { ...initialProcessingState },
  extractedTextStatus: { ...initialExtractedTextStatus },
  error: null,
  retry: { ...initialRetryState },
  currentProcessingSession: { ...initialSessionState },
  extraction: null,
  assessment: null,
  meta: null,
  applied: false,
  status: "idle",
  rawContent: "",
};

const assistantSlice = createSlice({
  name: "assistant",
  initialState,
  reducers: {
    setInputMode(state, action) {
      state.input.mode = action.payload;
      if (action.payload === "paste" && state.input.sourceType === "pdf") {
        state.input.sourceType = "text";
      } else if (action.payload === "upload") {
        state.input.sourceType = "pdf";
      }
    },
    setPastedText(state, action) {
      state.input.pastedText = action.payload;
    },
    setSourceType(state, action) {
      state.input.sourceType = action.payload;
    },
    setFileInfo(state, action) {
      state.input.fileInfo = action.payload;
    },
    clearFile(state) {
      state.input.fileInfo = null;
    },
    setProcessingStage(state, action) {
      const { stage, message, sessionId } = action.payload;
      state.processing.stage = stage;
      if (message) state.processing.stageMessage = message;
      if (sessionId) state.currentProcessingSession.sessionId = sessionId;
    },
    setExtractedResult(state, action) {
      const { success, extracted_text, source_type, metadata } = action.payload;
      state.extractedTextStatus = {
        success,
        extractedText: extracted_text,
        sourceType: source_type,
        metadata,
      };
      state.rawContent = extracted_text;
    },
    clearAssistant(state) {
      return {
        ...initialState,
        input: { ...initialInputState },
        processing: { ...initialProcessingState },
        extractedTextStatus: { ...initialExtractedTextStatus },
        retry: { ...initialRetryState },
        currentProcessingSession: { ...initialSessionState },
      };
    },
    markApplied(state) {
      state.applied = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(processDeviationInput.pending, (state, action) => {
        state.processing.status = "loading";
        state.status = "loading";
        state.error = null;
        state.applied = false;
        state.retry.canRetry = false;

        const arg = action.meta.arg;
        state.retry.lastPayload = {
          mode: arg.mode,
          text: arg.text,
          sourceType: arg.sourceType,
          fileName: arg.file?.name,
        };
        state.currentProcessingSession = {
          sessionId: "session-" + Date.now(),
          startedAt: new Date().toISOString(),
          completedAt: null,
        };
      })
      .addCase(processDeviationInput.fulfilled, (state, action) => {
        const { extractionRes, aiRes, sessionId } = action.payload;
        state.processing.status = "succeeded";
        state.processing.stage = "ready_for_review";
        state.processing.stageMessage =
          "Extracted fields automatically populated into deviation form.";
        state.status = "succeeded";

        if (extractionRes) {
          state.extractedTextStatus = {
            success: extractionRes.success,
            extractedText: extractionRes.extracted_text,
            sourceType: extractionRes.source_type,
            metadata: extractionRes.metadata,
          };
          state.rawContent = extractionRes.extracted_text;
        }

        if (aiRes) {
          const { extraction, assessment, ...meta } = aiRes;
          state.extraction = extraction;
          state.assessment = assessment;
          state.meta = meta;
        }

        state.applied = true;
        state.error = null;
        state.retry.canRetry = false;
        state.currentProcessingSession.completedAt = new Date().toISOString();
        if (sessionId) {
          state.currentProcessingSession.sessionId = sessionId;
        }
      })
      .addCase(processDeviationInput.rejected, (state, action) => {
        state.processing.status = "failed";
        state.processing.stage = "failed";
        state.status = "failed";

        const errPayload = action.payload;
        const msg =
          typeof errPayload === "string"
            ? errPayload
            : errPayload?.message || action.error?.message || "Processing failed";
        const title = errPayload?.title || "Processing Error";

        state.processing.stageMessage = msg;
        state.error = {
          title,
          message: msg,
          code: errPayload?.code || "PROCESSING_FAILED",
          stage: errPayload?.stage || state.processing.stage,
        };

        state.retry.canRetry = true;
        state.retry.retryCount += 1;
        state.currentProcessingSession.completedAt = new Date().toISOString();
      });
  },
});

export const {
  setInputMode,
  setPastedText,
  setSourceType,
  setFileInfo,
  clearFile,
  setProcessingStage,
  setExtractedResult,
  clearAssistant,
  markApplied,
} = assistantSlice.actions;

export default assistantSlice.reducer;
