import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";

export const emptyForm = {
  source: "manual",
  reported_by: "",
  occurred_on: "",
  detected_on: "",
  department: "",
  responsible_team: "",
  product_name: "",
  product_code: "",
  batch_number: "",
  manufacturing_stage: "",
  equipment: "",
  title: "",
  description: "",
  deviation_type: "",
  expected_condition: "",
  actual_condition: "",
  duration: "",
  parameter: "",
  immediate_action: "",
  batch_status: "",
  qa_notified: false,
  impact: "",
  severity: "",
  assessment_reason: "",
};

export const saveDeviation = createAsyncThunk(
  "deviations/save",
  async (payload, { rejectWithValue }) => {
    try {
      return await api.createDeviation(payload);
    } catch (err) {
      return rejectWithValue(err.message || "Failed to save deviation");
    }
  }
);

export const fetchDeviations = createAsyncThunk(
  "deviations/fetch",
  async (_, { rejectWithValue }) => {
    try {
      return await api.listDeviations({ limit: 8 });
    } catch (err) {
      return rejectWithValue(err.message || "Failed to load deviations");
    }
  }
);

export const fetchSummary = createAsyncThunk(
  "deviations/summary",
  async (_, { rejectWithValue }) => {
    try {
      return await api.getReportSummary();
    } catch (err) {
      return rejectWithValue(err.message || "Failed to load summary");
    }
  }
);

const initialState = {
  form: { ...emptyForm },
  aiSnapshot: null, // { ai_extraction, ai_assessment } to persist with the save
  saveStatus: "idle",
  saveError: null,
  lastSaved: null,
  list: [],
  listStatus: "idle",
  summary: null,
};

const deviationsSlice = createSlice({
  name: "deviations",
  initialState,
  reducers: {
    updateField(state, action) {
      const { name, value } = action.payload;
      state.form[name] = value;
    },
    resetForm(state) {
      state.form = { ...emptyForm };
      state.aiSnapshot = null;
      state.saveStatus = "idle";
      state.saveError = null;
      state.lastSaved = null;
    },
    // Copy the AI assistant output into the editable form (human-in-the-loop).
    applySuggestions(state, action) {
      const { extraction, assessment } = action.payload;
      if (extraction) {
        Object.entries(extraction).forEach(([key, value]) => {
          if (value !== null && value !== undefined && key in state.form) {
            state.form[key] = value;
          }
        });
        state.form.source = action.payload.source || "text";
      }
      if (assessment) {
        if (assessment.recommended_severity) state.form.severity = assessment.recommended_severity;
        if (assessment.recommended_impact) state.form.impact = assessment.recommended_impact;
        if (assessment.reason) state.form.assessment_reason = assessment.reason;
      }
      state.aiSnapshot = {
        ai_extraction: extraction ?? null,
        ai_assessment: assessment ?? null,
      };
    },
    clearSaveState(state) {
      state.saveStatus = "idle";
      state.saveError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(saveDeviation.pending, (state) => {
        state.saveStatus = "loading";
        state.saveError = null;
      })
      .addCase(saveDeviation.fulfilled, (state, action) => {
        state.saveStatus = "succeeded";
        state.lastSaved = action.payload;
        state.form = { ...emptyForm };
        state.aiSnapshot = null;
      })
      .addCase(saveDeviation.rejected, (state, action) => {
        state.saveStatus = "failed";
        state.saveError = action.payload || "Save failed";
      })
      .addCase(fetchDeviations.pending, (state) => {
        state.listStatus = "loading";
      })
      .addCase(fetchDeviations.fulfilled, (state, action) => {
        state.listStatus = "succeeded";
        state.list = action.payload?.items ?? [];
      })
      .addCase(fetchDeviations.rejected, (state) => {
        state.listStatus = "failed";
      })
      .addCase(fetchSummary.fulfilled, (state, action) => {
        state.summary = action.payload;
      });
  },
});

export const { updateField, resetForm, applySuggestions, clearSaveState } =
  deviationsSlice.actions;
export default deviationsSlice.reducer;
