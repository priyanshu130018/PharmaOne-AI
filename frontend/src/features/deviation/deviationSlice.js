import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";

export const emptyForm = {
  // AIVOA Core Fields
  site_plant: "",
  occurred_on: "", // Date of Occurrence
  detected_on: "",
  title: "", // Title / Short Description
  source: "manual",
  product_name: "", // Related Product / Material
  product_code: "",
  batch_number: "", // Batch / Lot Number
  description: "", // Detailed Description
  deviation_type: "",
  impact: "", // Initial Impact
  severity: "", // Initial Severity

  // Extracted Technical Details
  parameter: "",
  expected_condition: "", // Approved Range
  actual_condition: "", // Actual Value
  duration: "",
  manufacturing_stage: "",
  equipment: "",
  department: "",
  responsible_team: "",
  immediate_action: "",
  qa_notified: false,
  batch_status: "",
  assessment_reason: "",
  reported_by: "",
};

export const saveDeviation = createAsyncThunk(
  "deviation/save",
  async (payload, { rejectWithValue }) => {
    try {
      return await api.createDeviation(payload);
    } catch (err) {
      return rejectWithValue(err.message || "Failed to save deviation");
    }
  }
);

export const fetchDeviations = createAsyncThunk(
  "deviation/fetchList",
  async (params = { limit: 8 }, { rejectWithValue }) => {
    try {
      return await api.listDeviations(params);
    } catch (err) {
      return rejectWithValue(err.message || "Failed to load deviations");
    }
  }
);

export const fetchSummary = createAsyncThunk(
  "deviation/fetchSummary",
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
  originalAiExtraction: null,
  aiFields: {}, // { [fieldName]: true } - tracks fields auto-populated by AI
  userEditedFields: {}, // { [fieldName]: true } - tracks fields manually edited by user
  aiSnapshot: null, // { ai_extraction, ai_assessment } for audit trail
  saveStatus: "idle", // "idle" | "loading" | "succeeded" | "failed"
  saveError: null,
  lastSaved: null,
  list: [],
  listStatus: "idle",
  summary: null,
};

const deviationSlice = createSlice({
  name: "deviation",
  initialState,
  reducers: {
    updateField(state, action) {
      const { name, value } = action.payload;
      state.form[name] = value;
      // Mark field as explicitly modified by the user
      state.userEditedFields[name] = true;
    },
    resetForm(state) {
      state.form = { ...emptyForm };
      state.originalAiExtraction = null;
      state.aiFields = {};
      state.userEditedFields = {};
      state.aiSnapshot = null;
      state.saveStatus = "idle";
      state.saveError = null;
      state.lastSaved = null;
    },
    applySuggestions(state, action) {
      const { extraction, assessment, deviation, source } = action.payload;

      const normalizeDate = (val) => {
        if (!val) return "";
        const m = String(val).match(/\d{4}-\d{2}-\d{2}/);
        return m ? m[0] : String(val);
      };

      const incoming = {};

      // 1. StructuredDeviation mapping from LangGraph / Groq pipeline
      if (deviation) {
        if (deviation.site_plant) incoming.site_plant = deviation.site_plant;
        if (deviation.date_of_occurrence) {
          incoming.occurred_on = normalizeDate(deviation.date_of_occurrence);
        }
        if (deviation.title_short_description) {
          incoming.title = deviation.title_short_description;
        }
        if (deviation.detailed_description) {
          incoming.description = deviation.detailed_description;
        }
        if (deviation.deviation_type) {
          incoming.deviation_type = deviation.deviation_type;
        }
        if (deviation.related_product_material) {
          incoming.product_name = deviation.related_product_material;
        }
        if (deviation.batch_lot_number) {
          incoming.batch_number = deviation.batch_lot_number;
        }
        if (deviation.parameter) incoming.parameter = deviation.parameter;
        if (deviation.approved_range) incoming.expected_condition = deviation.approved_range;
        if (deviation.actual_value) incoming.actual_condition = deviation.actual_value;
        if (deviation.duration) incoming.duration = deviation.duration;
        if (deviation.manufacturing_stage) incoming.manufacturing_stage = deviation.manufacturing_stage;
        if (deviation.equipment) incoming.equipment = deviation.equipment;
        if (deviation.department) incoming.department = deviation.department;
        if (deviation.immediate_action) incoming.immediate_action = deviation.immediate_action;
        if (deviation.qa_notified !== null && deviation.qa_notified !== undefined) {
          incoming.qa_notified = Boolean(deviation.qa_notified);
        }
      }

      // 2. Backward-compatible extraction fields
      if (extraction) {
        Object.entries(extraction).forEach(([k, v]) => {
          if (v !== null && v !== undefined && v !== "") {
            if (k === "occurred_on" || k === "date_of_occurrence") {
              incoming.occurred_on = normalizeDate(v);
            } else if (k === "approved_range") {
              incoming.expected_condition = v;
            } else if (k === "actual_value") {
              incoming.actual_condition = v;
            } else if (k in state.form) {
              incoming[k] = v;
            }
          }
        });
      }

      // 3. Assessment initial severity & impact recommendations
      if (assessment) {
        if (assessment.recommended_severity) incoming.severity = assessment.recommended_severity;
        if (assessment.recommended_impact) incoming.impact = assessment.recommended_impact;
        if (assessment.reason) incoming.assessment_reason = assessment.reason;
      }

      if (source) {
        incoming.source = source;
      }

      // Safe Auto-Population: Never silently overwrite fields the user manually edited
      Object.entries(incoming).forEach(([field, value]) => {
        if (field in state.form) {
          if (!state.userEditedFields[field]) {
            state.form[field] = value;
            state.aiFields[field] = true;
          }
        }
      });

      state.originalAiExtraction = deviation || extraction || null;
      state.aiSnapshot = {
        ai_extraction: deviation || extraction || null,
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
        state.originalAiExtraction = null;
        state.aiFields = {};
        state.userEditedFields = {};
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
  deviationSlice.actions;
export default deviationSlice.reducer;
