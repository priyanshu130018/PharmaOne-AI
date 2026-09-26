import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  activeInputTab: "upload",
  showAllDetails: true,
  toast: null,
  highlightedField: null,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    setActiveInputTab(state, action) {
      state.activeInputTab = action.payload;
    },
    toggleShowAllDetails(state) {
      state.showAllDetails = !state.showAllDetails;
    },
    setToast(state, action) {
      state.toast = action.payload;
    },
    clearToast(state) {
      state.toast = null;
    },
    setHighlightedField(state, action) {
      state.highlightedField = action.payload;
    },
  },
});

export const {
  setActiveInputTab,
  toggleShowAllDetails,
  setToast,
  clearToast,
  setHighlightedField,
} = uiSlice.actions;
export default uiSlice.reducer;
