import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import BatchModuleView from "../BatchModuleView.jsx";
import LogDeviationForm from "../LogDeviationForm.jsx";
import deviationReducer, { prefillFromIpc } from "../../features/deviations/deviationsSlice.js";
import assistantReducer from "../../features/assistant/assistantSlice.js";
import { api } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  api: {
    listBatches: vi.fn(),
    getBatch: vi.fn(),
    createBatch: vi.fn(),
    addManufacturingStep: vi.fn(),
    createProcessCheck: vi.fn(),
    createRawMaterial: vi.fn(),
    createDeviation: vi.fn(),
    listDeviations: vi.fn(),
    getReportSummary: vi.fn(),
    getLinkedRecords: vi.fn(),
  },
}));

const mockBatch = {
  id: "b-055",
  batch_number: "API-2026-055",
  product_name: "Ibuprofen API",
  product_code: "IBU-400",
  recipe_version: "v3.1",
  site_plant: "Bengaluru",
  status: "In Progress",
  release_status: "Pending",
  created_at: "2026-09-30T10:00:00Z",
  raw_materials: [
    {
      id: "rm-1",
      name: "Isobutylbenzene",
      material_code: "RM-IBB-01",
      lot_number: "RM-2026-055",
      supplier_name: "ChemCorp",
      status: "Approved",
    },
  ],
  manufacturing_steps: [
    {
      id: "step-3",
      step_number: 3,
      name: "Step 3 — Reaction",
      status: "warning",
      warning_details: "Reactor temperature reached 79°C (Limit 70–75°C)",
    },
  ],
  in_process_checks: [
    {
      id: "ipc-1",
      step_id: "step-3",
      manufacturing_step_id: "step-3",
      parameter: "Temperature",
      specification: "70–75°C",
      actual_value: "79°C",
      status: "OUT-OF-LIMIT (OOL)",
      checked_by: "Operator K. Sharma",
      checked_at: "2026-09-30T14:30:00Z",
    },
  ],
};

describe("BatchModuleView - Batch-Centered Manufacturing Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listBatches.mockResolvedValue([mockBatch]);
    api.getBatch.mockResolvedValue(mockBatch);
  });

  it("1. displays 4 core tabs and the persistent active workspace banner", async () => {
    render(
      <BatchModuleView
        batchNumber="API-2026-055"
        onCreateDeviationFromIpc={vi.fn()}
      />
    );

    // Verify 4 tabs exist
    expect(await screen.findByTestId("tab-batches")).toBeInTheDocument();
    expect(screen.getByTestId("tab-raw_materials")).toBeInTheDocument();
    expect(screen.getByTestId("tab-manufacturing_steps")).toBeInTheDocument();
    expect(screen.getByTestId("tab-in_process_checks")).toBeInTheDocument();

    // Verify active batch banner is clearly visible
    const banner = await screen.findByTestId("active-batch-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/WORKING ON BATCH: API-2026-055/i);
    expect(banner).toHaveTextContent(/Product: Ibuprofen API \| Recipe: v3.1/i);
  });

  it("2. shows only raw materials for active batch in Raw Materials tab", async () => {
    render(
      <BatchModuleView
        batchNumber="API-2026-055"
        onCreateDeviationFromIpc={vi.fn()}
      />
    );

    await screen.findByTestId("active-batch-banner");

    // Click Raw Materials tab
    fireEvent.click(screen.getByTestId("tab-raw_materials"));

    // Verify header and raw material item
    expect(await screen.findByText(/Raw Materials Charged — Batch API-2026-055/i)).toBeInTheDocument();
    expect(screen.getByText("Isobutylbenzene")).toBeInTheDocument();
    expect(screen.getByText("RM-2026-055")).toBeInTheDocument();
    expect(screen.getByText("+ Add Raw Material")).toBeInTheDocument();
  });

  it("3. shows only manufacturing steps for active batch in Manufacturing Steps tab", async () => {
    render(
      <BatchModuleView
        batchNumber="API-2026-055"
        onCreateDeviationFromIpc={vi.fn()}
      />
    );

    await screen.findByTestId("active-batch-banner");

    // Click Manufacturing Steps tab
    fireEvent.click(screen.getByTestId("tab-manufacturing_steps"));

    // Verify header and step
    expect(await screen.findByText(/Manufacturing Execution Steps — Batch API-2026-055/i)).toBeInTheDocument();
    expect(screen.getByText("Step 3 — Reaction")).toBeInTheDocument();
    expect(screen.getByText("+ Add Manufacturing Step")).toBeInTheDocument();
  });

  it("4. shows IPC report (Total / Passed / OOL) and Create Deviation button for OOL check", async () => {
    const handleCreateDeviation = vi.fn();
    render(
      <BatchModuleView
        batchNumber="API-2026-055"
        onCreateDeviationFromIpc={handleCreateDeviation}
      />
    );

    await screen.findByTestId("active-batch-banner");

    // Click In-Process Checks tab
    fireEvent.click(screen.getByTestId("tab-in_process_checks"));

    // Verify simple IPC report
    const summary = await screen.findByTestId("ipc-summary-report");
    expect(summary).toBeInTheDocument();
    expect(summary).toHaveTextContent(/Total Checks/i);
    expect(summary).toHaveTextContent("1");
    expect(summary).toHaveTextContent(/OUT-OF-LIMIT \(OOL\)/i);

    // Verify table row & excursion indicator
    expect(screen.getAllByText("79°C").length).toBeGreaterThan(0);
    expect(screen.getAllByText("70–75°C").length).toBeGreaterThan(0);

    // Verify "Create Deviation for Batch API-2026-055" button
    const devButtons = screen.getAllByRole("button", { name: /Create Deviation for Batch API-2026-055/i });
    expect(devButtons.length).toBeGreaterThan(0);

    // Click Create Deviation button
    fireEvent.click(devButtons[0]);

    // Ensure callback called with batch, product, raw material, step, parameter, limits
    expect(handleCreateDeviation).toHaveBeenCalledTimes(1);
    const payload = handleCreateDeviation.mock.calls[0][0];
    expect(payload.batch_number).toBe("API-2026-055");
    expect(payload.product_name).toBe("Ibuprofen API");
    expect(payload.raw_material_name).toBe("Isobutylbenzene");
    expect(payload.manufacturing_stage).toBe("Step 3 — Reaction");
    expect(payload.parameter).toBe("Temperature");
    expect(payload.actual_condition).toBe("79°C");
    expect(payload.expected_condition).toBe("70–75°C");
  });

  it("5. verifies deviation intake form is fully populated from batch/step/IPC with no empty known fields", () => {
    const store = configureStore({
      reducer: {
        deviations: deviationReducer,
        assistant: assistantReducer,
      },
    });

    const ipcPayload = {
      batch_id: "b-055",
      batch_number: "API-2026-055",
      product_name: "Ibuprofen API",
      recipe_version: "v3.1",
      site_plant: "Bengaluru",
      raw_material_name: "Isobutylbenzene",
      manufacturing_stage: "Step 3 — Reaction",
      process_operation: "Reaction",
      equipment: "Reactor R-101",
      department: "API Manufacturing",
      parameter: "Temperature",
      expected_condition: "70–75°C",
      actual_condition: "79°C",
      duration: "15 minutes",
      reported_by: "Operator K. Sharma",
      source: "manufacturing",
      deviation_type: "process",
      severity: "major",
      impact: "product_quality",
      batch_status: "quarantined",
      immediate_action: "Reaction heating paused; cooling applied and QA notified. Batch quarantined pending QA investigation.",
      qa_notified: true,
      title: "Temperature process excursion on Batch API-2026-055 at Step 3 — Reaction",
      description: "During manufacturing of Batch API-2026-055 at Step 3 (Reaction), temperature reached 79°C, exceeding the approved process limit of 70–75°C.",
    };

    store.dispatch(prefillFromIpc(ipcPayload));

    render(
      <Provider store={store}>
        <LogDeviationForm />
      </Provider>
    );

    // Form fields verification
    expect(screen.getByDisplayValue("API-2026-055")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Ibuprofen API")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Bengaluru")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Operator K. Sharma")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Temperature process excursion on Batch API-2026-055 at Step 3 — Reaction")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/During manufacturing of Batch API-2026-055 at Step 3 \(Reaction\), temperature reached 79°C, exceeding the approved process limit of 70–75°C\./i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Reactor R-101")).toBeInTheDocument();
    expect(screen.getByDisplayValue("API Manufacturing")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Step 3 — Reaction")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Reaction")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Temperature")).toBeInTheDocument();
    expect(screen.getByDisplayValue("15 minutes")).toBeInTheDocument();
    expect(screen.getByDisplayValue("70–75°C")).toBeInTheDocument();
    expect(screen.getByDisplayValue("79°C")).toBeInTheDocument();
    expect(screen.getByLabelText(/QA Notified upon detection/i)).toBeChecked();
  });
});
