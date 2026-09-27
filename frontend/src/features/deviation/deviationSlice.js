import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";

export const emptyForm = {
  // AIVOA Core Fields
  company: "",
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
  highlightedFields: {}, // { [fieldName]: true } - tracks fields updated by chat AI
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
      state.form = state.form || {};
      state.userEditedFields = state.userEditedFields || {};
      state.highlightedFields = state.highlightedFields || {};
      state.form[name] = value;
      // Mark field as explicitly modified by the user
      state.userEditedFields[name] = true;
      // Remove the green highlight when the user manually edits that field
      delete state.highlightedFields[name];
    },
    updateMultipleFields(state, action) {
      const { changes } = action.payload || {};
      if (!changes) return;
      state.form = state.form || {};
      state.userEditedFields = state.userEditedFields || {};
      state.highlightedFields = state.highlightedFields || {};
      const aliasMap = {
        site: "site_plant",
        plant: "site_plant",
        facility: "site_plant",
        date: "occurred_on",
        date_of_occurrence: "occurred_on",
        title_short_description: "title",
        detailed_description: "description",
        product: "product_name",
        related_product_material: "product_name",
        batch: "batch_number",
        batch_lot_number: "batch_number",
        approved_range: "expected_condition",
        actual_value: "actual_condition",
        initial_impact: "impact",
        initial_severity: "severity",
      };

      if (Array.isArray(changes)) {
        changes.forEach((item) => {
          if (!item || !item.field) return;
          const canonicalKey = aliasMap[item.field] || item.field;
          const val = item.new_value !== undefined ? item.new_value : item.value;
          if (canonicalKey in state.form) {
            state.form[canonicalKey] = val;
            state.userEditedFields[canonicalKey] = true;
            state.highlightedFields[canonicalKey] = true;
          }
        });
      } else if (typeof changes === "object") {
        Object.entries(changes).forEach(([rawKey, val]) => {
          const canonicalKey = aliasMap[rawKey] || rawKey;
          if (canonicalKey in state.form) {
            state.form[canonicalKey] = val;
            state.userEditedFields[canonicalKey] = true;
            state.highlightedFields[canonicalKey] = true;
          }
        });
      }
    },
    clearHighlightedFields(state) {
      state.highlightedFields = {};
    },
    resetForm(state) {
      state.form = { ...emptyForm };
      state.originalAiExtraction = null;
      state.aiFields = {};
      state.userEditedFields = {};
      state.highlightedFields = {};
      state.aiSnapshot = null;
      state.saveStatus = "idle";
      state.saveError = null;
      state.lastSaved = null;
    },
    applySuggestions(state, action) {
      const { extraction, assessment, deviation, source } = action.payload;

      const normalizeDate = (val) => {
        if (!val) return "";
        const str = String(val).trim();
        // 1. Check YYYY-MM-DD
        const ym = str.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
        if (ym) return `${ym[1]}-${ym[2]}-${ym[3]}`;
        // 2. Check DD/MM/YYYY or DD-MM-YYYY
        const dm = str.match(/\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b/);
        if (dm) {
          const day = dm[1].padStart(2, "0");
          const month = dm[2].padStart(2, "0");
          const year = dm[3];
          return `${year}-${month}-${day}`;
        }
        // 3. Named month dates like "27 September 2026"
        const mNames = {
          jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
          jul: "07", aug: "08", sep: "09", sept: "09", oct: "10", nov: "11", dec: "12",
          january: "01", february: "02", march: "03", april: "04", june: "06",
          july: "07", august: "08", september: "09", october: "10", november: "11", december: "12",
        };
        const textMonth = str.match(/\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b/);
        if (textMonth && mNames[textMonth[2].toLowerCase()]) {
          return `${textMonth[3]}-${mNames[textMonth[2].toLowerCase()]}-${textMonth[1].padStart(2, "0")}`;
        }
        const monthText = str.match(/\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b/);
        if (monthText && mNames[monthText[1].toLowerCase()]) {
          return `${monthText[3]}-${mNames[monthText[1].toLowerCase()]}-${monthText[2].padStart(2, "0")}`;
        }
        // 4. Fallback: Parse date using local date components to avoid UTC timezone offset shifts
        const parsed = Date.parse(str);
        if (!isNaN(parsed)) {
          const d = new Date(parsed);
          const year = d.getFullYear();
          const month = String(d.getMonth() + 1).padStart(2, "0");
          const day = String(d.getDate()).padStart(2, "0");
          return `${year}-${month}-${day}`;
        }
        return str;
      };

      const incoming = {};

      // 1. StructuredDeviation mapping from LangGraph / Groq pipeline
      if (deviation) {
        if (deviation.site_plant) incoming.site_plant = deviation.site_plant;
        if (deviation.company) incoming.company = deviation.company;
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
          incoming.deviation_type = String(deviation.deviation_type).toLowerCase().trim();
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
        if (deviation.batch_status) incoming.batch_status = String(deviation.batch_status).toLowerCase().trim();
        if (deviation.qa_notified !== null && deviation.qa_notified !== undefined) {
          incoming.qa_notified = Boolean(deviation.qa_notified);
        }
      }

      // 2. Backward-compatible extraction fields
      if (extraction) {
        if (extraction.site_plant && !incoming.site_plant) {
          incoming.site_plant = extraction.site_plant;
        }
        if (extraction.company && !incoming.company) {
          incoming.company = extraction.company;
        }
        if ((extraction.occurred_on || extraction.date_of_occurrence) && !incoming.occurred_on) {
          incoming.occurred_on = normalizeDate(extraction.occurred_on || extraction.date_of_occurrence);
        }
        Object.entries(extraction).forEach(([k, v]) => {
          if (v !== null && v !== undefined && v !== "") {
            if (k === "occurred_on" || k === "date_of_occurrence") {
              if (!incoming.occurred_on) incoming.occurred_on = normalizeDate(v);
            } else if (k === "site_plant" || k === "site") {
              if (!incoming.site_plant) incoming.site_plant = v;
            } else if (k === "company" || k === "company_name") {
              if (!incoming.company) incoming.company = v;
            } else if (k === "approved_range") {
              incoming.expected_condition = v;
            } else if (k === "actual_value") {
              incoming.actual_condition = v;
            } else if (k === "batch_lot_number") {
              incoming.batch_number = v;
            } else if (k === "related_product_material") {
              incoming.product_name = v;
            } else if (k === "title_short_description") {
              incoming.title = v;
            } else if (k === "detailed_description") {
              incoming.description = v;
            } else if (k === "deviation_type") {
              incoming.deviation_type = String(v).toLowerCase().trim();
            } else if (k in state.form) {
              incoming[k] = v;
            }
          }
        });
      }

      // 3. Assessment initial severity & impact recommendations
      if (assessment) {
        if (assessment.recommended_severity) {
          incoming.severity = String(assessment.recommended_severity).toLowerCase().trim();
        }
        if (assessment.recommended_impact) {
          incoming.impact = String(assessment.recommended_impact).toLowerCase().trim();
        }
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
        // The full form remains visible on the left; user edits and reviewed fields stay intact.
        state.saveError = null;
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

export const {
  updateField,
  updateMultipleFields,
  clearHighlightedFields,
  resetForm,
  applySuggestions,
  clearSaveState,
} = deviationSlice.actions;
export default deviationSlice.reducer;
