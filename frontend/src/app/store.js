import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../features/auth/authSlice.js";
import deviationsReducer from "../features/deviations/deviationsSlice.js";
import assistantReducer from "../features/assistant/assistantSlice.js";
import aiProcessingReducer from "../features/ai/aiProcessingSlice.js";
import assessmentReducer from "../features/assessment/assessmentSlice.js";
import uiReducer from "../features/ui/uiSlice.js";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    deviation: deviationsReducer,
    deviations: deviationsReducer,
    assistant: assistantReducer,
    aiProcessing: aiProcessingReducer,
    assessment: assessmentReducer,
    ui: uiReducer,
  },
});
