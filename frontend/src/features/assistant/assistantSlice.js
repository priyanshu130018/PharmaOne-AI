import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";

// Calls POST /deviations/process. Nothing is persisted; the response is a
// best-effort extraction plus an AI risk assessment for the reporter to review.
export const processContent = createAsyncThunk(
  "assistant/process",
  async ({ content, source = "text" }, { rejectWithValue }) => {
    try {
      return await api.processDeviation(content, source);
    } catch (err) {
      return rejectWithValue(err.message || "Failed to process content");
    }
  }
);

const initialState = {
  rawContent: "",
  status: "idle", // idle | loading | succeeded | failed
  error: null,
  extraction: null,
  assessment: null,
  meta: null, // { model, provider, is_stub, requires_human_review }
  applied: false, // whether the current result has been copied into the form
};

const assistantSlice = createSlice({
  name: "assistant",
  initialState,
  reducers: {
    setRawContent(state, action) {
      state.rawContent = action.payload;
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
      .addCase(processContent.pending, (state) => {
        state.status = "loading";
        state.error = null;
        state.applied = false;
      })
      .addCase(processContent.fulfilled, (state, action) => {
        const { extraction, assessment, ...meta } = action.payload;
        state.status = "succeeded";
        state.extraction = extraction;
        state.assessment = assessment;
        state.meta = meta;
      })
      .addCase(processContent.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload || "Processing failed";
      });
  },
});

export const { setRawContent, markApplied, clearAssistant } = assistantSlice.actions;
export default assistantSlice.reducer;
