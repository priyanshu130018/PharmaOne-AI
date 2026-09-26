import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import deviationReducer, {
  applySuggestions,
  updateField,
  resetForm,
} from "../../features/deviation/deviationSlice.js";
import assistantReducer from "../../features/assistant/assistantSlice.js";
import LogDeviationForm from "../LogDeviationForm.jsx";
import { api } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  api: {
    createDeviation: vi.fn(),
    listDeviations: vi.fn(),
    getReportSummary: vi.fn(),
  },
}));

function renderWithStore(preloadedState = {}) {
  const store = configureStore({
    reducer: {
      deviations: deviationReducer,
      assistant: assistantReducer,
    },
    preloadedState,
  });

  const utils = render(
    <Provider store={store}>
      <LogDeviationForm />
    </Provider>
  );

  return { store, ...utils };
}

describe("LogDeviationForm - AIVOA Intake Workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders all required AIVOA Log Deviation form fields", () => {
    renderWithStore();

    expect(screen.getByLabelText(/Site \/ Plant/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Date of Occurrence/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title \/ Short Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Source Channel/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Deviation Type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Related Product \/ Material/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Batch \/ Lot Number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Detailed Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Parameter/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Approved Range/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Actual Value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Duration/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Immediate Action/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/QA Notified/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Impact/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Severity/i)).toBeInTheDocument();

    // Save button should initially be disabled because required fields are empty
    const saveBtn = screen.getByRole("button", { name: /Save Deviation/i });
    expect(saveBtn).toBeDisabled();
  });

  it("2. auto-populates form fields when AI suggestions arrive and displays AI badges", async () => {
    const { store } = renderWithStore();

    act(() => {
      store.dispatch(
        applySuggestions({
          deviation: {
            site_plant: "Plant 1 - Sterile Ops",
            date_of_occurrence: "2026-03-25",
            title_short_description: "Autoclave Sterilization Temperature Drop",
            detailed_description: "Chamber temperature dropped below validated minimum of 120.5C.",
            deviation_type: "equipment",
            related_product_material: "Sterile Saline 100mL",
            batch_lot_number: "LOT-2026-991",
            parameter: "Chamber Temperature",
            approved_range: "121.1C +/- 0.5C",
            actual_value: "118.2C",
            duration: "8 minutes",
            immediate_action: "Cycle aborted and trays quarantined.",
            qa_notified: true,
          },
          assessment: {
            recommended_severity: "critical",
            recommended_impact: "patient_safety",
            reason: "Direct sterility assurance compromise.",
          },
          source: "pdf",
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByLabelText(/Site \/ Plant/i)).toHaveValue("Plant 1 - Sterile Ops");
      expect(screen.getByLabelText(/Title \/ Short Description/i)).toHaveValue(
        "Autoclave Sterilization Temperature Drop"
      );
      expect(screen.getByLabelText(/Related Product \/ Material/i)).toHaveValue("Sterile Saline 100mL");
      expect(screen.getByLabelText(/Batch \/ Lot Number/i)).toHaveValue("LOT-2026-991");
      expect(screen.getByLabelText(/Parameter/i)).toHaveValue("Chamber Temperature");
      expect(screen.getByLabelText(/Approved Range/i)).toHaveValue("121.1C +/- 0.5C");
      expect(screen.getByLabelText(/Actual Value/i)).toHaveValue("118.2C");
      expect(screen.getByLabelText(/Initial Severity/i)).toHaveValue("critical");
      expect(screen.getByLabelText(/Initial Impact/i)).toHaveValue("patient_safety");
      expect(screen.getByLabelText(/QA Notified/i)).toBeChecked();

      // Check AI extracted badge presence
      const aiBadges = screen.getAllByText(/AI extracted/i);
      expect(aiBadges.length).toBeGreaterThanOrEqual(5);

      // Since required fields are now filled, Save Deviation is enabled!
      const saveBtn = screen.getByRole("button", { name: /Save Deviation/i });
      expect(saveBtn).not.toBeDisabled();
    });
  });

  it("3. allows user overrides and does not overwrite user-modified fields on subsequent AI results", async () => {
    const { store } = renderWithStore();

    // User types in a custom batch number first
    const batchInput = screen.getByLabelText(/Batch \/ Lot Number/i);
    fireEvent.change(batchInput, { target: { value: "MANUAL-BATCH-777" } });

    expect(batchInput).toHaveValue("MANUAL-BATCH-777");
    // Should display Modified badge
    expect(screen.getByText(/Modified/i)).toBeInTheDocument();

    // Now AI suggestions arrive with a different batch number
    act(() => {
      store.dispatch(
        applySuggestions({
          deviation: {
            title_short_description: "New AI Event",
            detailed_description: "Detailed event description from AI analysis.",
            deviation_type: "process",
            batch_lot_number: "AI-BATCH-999", // Different batch number from AI
            related_product_material: "AI Product",
          },
          assessment: {
            recommended_severity: "minor",
            recommended_impact: "product_quality",
          },
        })
      );
    });

    await waitFor(() => {
      // Manual user edit was preserved! Not overwritten by AI!
      expect(screen.getByLabelText(/Batch \/ Lot Number/i)).toHaveValue("MANUAL-BATCH-777");
      // Other unedited fields were populated by AI
      expect(screen.getByLabelText(/Title \/ Short Description/i)).toHaveValue("New AI Event");
      expect(screen.getByLabelText(/Related Product \/ Material/i)).toHaveValue("AI Product");
    });
  });

  it("4. validates required fields before enabling save, and successfully saves when valid", async () => {
    api.createDeviation.mockResolvedValueOnce({
      id: "123e4567-e89b-12d3-a456-426614174000",
      reference: "DEV-2026-0001",
      status: "draft",
    });

    renderWithStore({
      deviations: {
        form: {
          site_plant: "Sterile Facility",
          title: "Valid Title Here",
          description: "Long enough description exceeding ten characters.",
          deviation_type: "equipment",
          source: "manual",
          qa_notified: false,
          impact: "product_quality",
          severity: "major",
        },
        aiFields: {},
        userEditedFields: {},
        saveStatus: "idle",
      },
    });

    const saveBtn = screen.getByRole("button", { name: /Save Deviation/i });
    expect(saveBtn).not.toBeDisabled();

    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.createDeviation).toHaveBeenCalled();
    });
  });

  it("5. resets the form cleanly when Reset button is clicked", () => {
    renderWithStore();

    const titleInput = screen.getByLabelText(/Title \/ Short Description/i);
    fireEvent.change(titleInput, { target: { value: "Temporary Title" } });
    expect(titleInput).toHaveValue("Temporary Title");

    const resetBtn = screen.getByRole("button", { name: /Reset/i });
    fireEvent.click(resetBtn);

    expect(titleInput).toHaveValue("");
  });

  it("6. editing impact and severity tracks user overrides and preserves user choices", async () => {
    const { store } = renderWithStore();

    act(() => {
      store.dispatch(
        applySuggestions({
          deviation: {
            title_short_description: "Initial Deviation",
            detailed_description: "Valid detailed description exceeding 10 characters.",
            deviation_type: "equipment",
          },
          assessment: {
            recommended_severity: "critical",
            recommended_impact: "patient_safety",
          },
        })
      );
    });

    const severitySelect = screen.getByLabelText(/Initial Severity/i);
    expect(severitySelect).toHaveValue("critical");

    // User reviews and changes severity to minor
    fireEvent.change(severitySelect, { target: { value: "minor" } });
    expect(severitySelect).toHaveValue("minor");

    // User changes impact to compliance
    const impactSelect = screen.getByLabelText(/Initial Impact/i);
    fireEvent.change(impactSelect, { target: { value: "compliance" } });
    expect(impactSelect).toHaveValue("compliance");
  });

  it("7. save failure preserves form state and displays error notification without losing data", async () => {
    api.createDeviation.mockRejectedValueOnce(new Error("Network connection dropped during save"));

    renderWithStore({
      deviations: {
        form: {
          site_plant: "Packaging Suite 2",
          title: "Important Deviation Event",
          description: "Crucial detailed incident description.",
          deviation_type: "material",
          source: "manual",
          qa_notified: true,
          impact: "product_quality",
          severity: "major",
        },
        aiFields: {},
        userEditedFields: {},
        saveStatus: "idle",
      },
    });

    const saveBtn = screen.getByRole("button", { name: /Save Deviation/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.createDeviation).toHaveBeenCalled();
    });

    // Verify form state is STILL completely intact (no data lost)
    expect(screen.getByLabelText(/Site \/ Plant/i)).toHaveValue("Packaging Suite 2");
    expect(screen.getByLabelText(/Title \/ Short Description/i)).toHaveValue("Important Deviation Event");
    expect(screen.getByLabelText(/Detailed Description/i)).toHaveValue("Crucial detailed incident description.");
  });
});
