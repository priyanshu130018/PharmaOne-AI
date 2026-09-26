import { configureStore } from "@reduxjs/toolkit";
import deviationReducer from "../features/deviation/deviationSlice.js";
import deviationsReducer from "../features/deviations/deviationsSlice.js";
import aiProcessingReducer from "../features/ai/aiProcessingSlice.js";
import assessmentReducer from "../features/assessment/assessmentSlice.js";
import uiReducer from "../features/ui/uiSlice.js";
import assistantReducer from "../features/assistant/assistantSlice.js";

export const store = configureStore({
  reducer: {
    deviation: deviationReducer,
    deviations: deviationsReducer,
    assistant: assistantReducer,
    aiProcessing: aiProcessingReducer,
    assessment: assessmentReducer,
    ui: uiReducer,
  },
});
