import { configureStore } from "@reduxjs/toolkit";
import deviationsReducer from "../features/deviations/deviationsSlice.js";
import assistantReducer from "../features/assistant/assistantSlice.js";

export const store = configureStore({
  reducer: {
    deviations: deviationsReducer,
    assistant: assistantReducer,
  },
});
