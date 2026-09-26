import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";
import { applySuggestions } from "../deviations/deviationsSlice.js";

// Multi-stage deviation extraction and AI analysis pipeline
export const processDeviationInput = createAsyncThunk(
  "assistant/processInput",
  async ({ file, text, sourceType = "text", mode = "paste" }, { dispatch, rejectWithValue }) => {
    const sessionId = "session-" + Date.now();
    try {
      let extractionRes;

      if (mode === "upload" && file) {
        // Stage 1: Uploading
        dispatch(
          setProcessingStage({
            stage: "uploading",
            message: "Uploading document…",
            sessionId,
          })
        );

        // Stage 2: Checking document
        dispatch(
          setProcessingStage({
            stage: "checking",
            message: "Checking document format and integrity…",
            sessionId,
          })
        );

        // Stage 3: Extracting text
        dispatch(
          setProcessingStage({
            stage: "extracting",
            message: "Extracting text from document…",
            sessionId,
          })
        );

        extractionRes = await api.extractDocument(file);
      } else {
        // Pasted text / email flow
        dispatch(
          setProcessingStage({
            stage: "checking",
            message: "Checking document and validating input…",
            sessionId,
          })
        );

        dispatch(
          setProcessingStage({
            stage: "extracting",
            message: "Normalizing text content…",
            sessionId,
          })
        );

        extractionRes = await api.extractText(text, sourceType);
      }

      if (!extractionRes || !extractionRes.success) {
        const errorMsg =
          extractionRes?.error?.message ||
          "Could not extract usable text from the provided document.";
        return rejectWithValue({
          message: errorMsg,
          code: extractionRes?.error?.code || "EXTRACTION_FAILED",
          stage: "extracting",
          sessionId,
        });
      }

      dispatch(setExtractedResult(extractionRes));

      // Stage 4: Preparing AI analysis
      dispatch(
        setProcessingStage({
          stage: "analyzing",
          message: "Preparing AI analysis and risk assessment…",
          sessionId,
        })
      );

      const aiRes = await api.processDeviation(
        extractionRes.extracted_text,
        extractionRes.source_type || sourceType
      );

      // Automatically populate the left-hand form with extracted fields
      if (aiRes?.extraction || aiRes?.assessment) {
        dispatch(
          applySuggestions({
            extraction: aiRes.extraction,
            assessment: aiRes.assessment,
            source: extractionRes.source_type || sourceType,
          })
        );
      }

      return {
        extractionRes,
        aiRes,
        sessionId,
      };
    } catch (err) {
      return rejectWithValue({
        message: err.message || "Failed to process deviation input.",
        code: err.detail || err.name || "PROCESS_ERROR",
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
  stage: "idle", // "idle" | "uploading" | "checking" | "extracting" | "analyzing" | "succeeded" | "failed"
  stageMessage: "",
};

const initialExtractedTextStatus = {
  success: false,
  extractedText: "",
  sourceType: "pdf",
  metadata: null, // { filename, page_count, character_count, ocr_applied, ocr_available, warnings }
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
  // Required feature slices
  input: { ...initialInputState },
  processing: { ...initialProcessingState },
  extractedTextStatus: { ...initialExtractedTextStatus },
  error: null,
  retry: { ...initialRetryState },
  currentProcessingSession: { ...initialSessionState },

  // Downstream analysis compatibility
  rawContent: "",
  status: "idle",
  extraction: null,
  assessment: null,
  meta: null,
  applied: false,
};

const assistantSlice = createSlice({
  name: "assistant",
  initialState,
  reducers: {
    setInputMode(state, action) {
      state.input.mode = action.payload;
      state.input.sourceType = action.payload === "upload" ? "pdf" : "text";
      state.error = null;
    },
    setPastedText(state, action) {
      state.input.pastedText = action.payload;
      state.rawContent = action.payload;
      state.error = null;
    },
    setRawContent(state, action) {
      state.input.pastedText = action.payload;
      state.rawContent = action.payload;
      state.error = null;
    },
    setFileInfo(state, action) {
      state.input.fileInfo = action.payload;
      state.error = null;
    },
    clearFile(state) {
      state.input.fileInfo = null;
      state.error = null;
    },
    setProcessingStage(state, action) {
      const { stage, message, sessionId } = action.payload;
      state.processing.stage = stage;
      state.processing.stageMessage = message;
      if (sessionId && !state.currentProcessingSession.sessionId) {
        state.currentProcessingSession.sessionId = sessionId;
        state.currentProcessingSession.startedAt = new Date().toISOString();
      }
    },
    setExtractedResult(state, action) {
      const res = action.payload;
      state.extractedTextStatus = {
        success: res.success,
        extractedText: res.extracted_text,
        sourceType: res.source_type,
        metadata: res.metadata,
      };
      state.rawContent = res.extracted_text;
    },
    markApplied(state) {
      state.applied = true;
    },
    clearAssistant() {
      return { ...initialState };
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
        // Keep payload for retry (omitting raw file binary to stay serializable)
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
        state.processing.stage = "succeeded";
        state.processing.stageMessage = "AI analysis complete — fields applied to form.";
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

        state.processing.stageMessage = msg;
        state.error = msg;
        state.retry.canRetry = true;
        state.retry.retryCount += 1;
        state.currentProcessingSession.completedAt = new Date().toISOString();
      });
  },
});

export const {
  setInputMode,
  setPastedText,
  setRawContent,
  setFileInfo,
  clearFile,
  setProcessingStage,
  setExtractedResult,
  markApplied,
  clearAssistant,
} = assistantSlice.actions;

export default assistantSlice.reducer;
