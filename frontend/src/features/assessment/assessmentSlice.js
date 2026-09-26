import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  recommendedImpact: null, // "patient_safety" | "product_quality" | "data_integrity" | "compliance" | "supply" | "none"
  impactReason: null,
  recommendedSeverity: null, // "minor" | "major" | "critical"
  severityReason: null,
  evidence: [],
  retrievedSources: [],
  uncertainties: [],
  criteriaNote: "Configurable/demo risk criteria — NOT a universal regulatory severity lookup. ICH Q9 is methodology guidance only. Final impact and severity must be confirmed by the reviewer against approved company procedures.",
  requiresHumanReview: true,
  ragAvailable: true,
  ragNotes: null,
  model: null,
  provider: null,
  isStub: false,
  rawAssessment: null,
};

const assessmentSlice = createSlice({
  name: "assessment",
  initialState,
  reducers: {
    setAssessment(state, action) {
      const { assessment, evidence, retrieved_sources, rag_available, rag_notes, model, provider, is_stub, requires_human_review } = action.payload;

      if (assessment) {
        state.recommendedImpact = assessment.recommended_impact || assessment.impact || null;
        state.recommendedSeverity = assessment.recommended_severity || assessment.severity || null;
        state.impactReason = assessment.impact_reason || assessment.reason || null;
        state.severityReason = assessment.severity_reason || assessment.reason || null;
        state.uncertainties = assessment.uncertainties || [];
        if (assessment.criteria_note) {
          state.criteriaNote = assessment.criteria_note;
        }
        state.rawAssessment = assessment;
      }

      state.evidence = evidence || assessment?.evidence || [];
      state.retrievedSources = retrieved_sources || [];
      state.ragAvailable = rag_available !== undefined ? rag_available : true;
      state.ragNotes = rag_notes || null;
      state.model = model || null;
      state.provider = provider || null;
      state.isStub = Boolean(is_stub);
      state.requiresHumanReview = requires_human_review !== undefined ? requires_human_review : true;
    },
    clearAssessment(state) {
      return { ...initialState };
    },
  },
});

export const { setAssessment, clearAssessment } = assessmentSlice.actions;
export default assessmentSlice.reducer;
