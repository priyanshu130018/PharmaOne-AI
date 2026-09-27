import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import assistantReducer from "../../features/assistant/assistantSlice.js";
import deviationsReducer, { updateField } from "../../features/deviations/deviationsSlice.js";
import AiAssistantPanel from "../AiAssistantPanel.jsx";
import { api } from "../../api/client.js";

// Mock API client methods
vi.mock("../../api/client.js", () => ({
  api: {
    extractDocument: vi.fn(),
    extractText: vi.fn(),
    processDeviation: vi.fn(),
    sendDeviationChat: vi.fn(),
  },
}));

function renderWithStore(preloadedState = {}) {
  const store = configureStore({
    reducer: {
      assistant: assistantReducer,
      deviations: deviationsReducer,
    },
    preloadedState,
  });

  const utils = render(
    <Provider store={store}>
      <AiAssistantPanel />
    </Provider>
  );

  return { store, ...utils };
}

describe("AiAssistantPanel - AI Deviation Assistant", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. initial state: renders only AI Deviation Assistant and empty chatbot with composer", () => {
    renderWithStore();

    // 1. Header
    expect(screen.getByText("AI Deviation Assistant")).toBeInTheDocument();

    // 2. Empty conversation placeholder
    expect(
      screen.getByText(/Describe your deviation or ask me to update any field in the form/i)
    ).toBeInTheDocument();

    // 3. Composer fixed at bottom with attachment icon and send button
    expect(screen.getByLabelText(/Attach document/i)).toBeInTheDocument();
    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    expect(chatInput).toBeInTheDocument();
    expect(chatInput).not.toBeDisabled();
    expect(screen.getByRole("button", { name: /Send message/i })).toBeInTheDocument();

    // 4. Strict layout verification: No form fields, no large extraction cards, no severity report on the right
    expect(screen.queryByLabelText(/Date of Occurrence/i)).toBeNull();
    expect(screen.queryByLabelText(/Detailed Description/i)).toBeNull();
    expect(screen.queryByText(/Values Applied to Form/i)).toBeNull();
    expect(screen.queryByText(/DEVIATION SEVERITY REPORT/i)).toBeNull();
    expect(screen.queryByText(/Analysis Complete/i)).toBeNull();
    expect(screen.queryByText(/Upload PDF \/ Document/i)).toBeNull();
  });

  it("2. natural-language form update: sets site/plant via chat and updates left form live", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "update_form",
      changes: {
        site_plant: "Demo Manufacturing Site",
        site: "Demo Manufacturing Site",
      },
      message: "Updated Site / Plant to Demo Manufacturing Site.",
      response: "Updated Site / Plant to Demo Manufacturing Site.",
    });

    const { store } = renderWithStore();

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, { target: { value: "Set the site to Demo Manufacturing Site." } });

    const sendBtn = screen.getByRole("button", { name: /Send message/i });
    fireEvent.click(sendBtn);

    // Verify user message in chat
    expect(screen.getByText("Set the site to Demo Manufacturing Site.")).toBeInTheDocument();

    // Verify API called
    await waitFor(() => {
      expect(api.sendDeviationChat).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Set the site to Demo Manufacturing Site.",
        })
      );
    });

    // Verify bot confirmation in chat
    await waitFor(() => {
      expect(screen.getByText("Updated Site / Plant to Demo Manufacturing Site.")).toBeInTheDocument();
    });

    // Verify Redux state (which updates the LEFT form) was updated live!
    expect(store.getState().deviations.form.site_plant).toBe("Demo Manufacturing Site");
    expect(store.getState().deviations.userEditedFields.site_plant).toBe(true);
  });

  it("3. natural-language form update: updates batch and title simultaneously", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "update_form",
      changes: {
        batch_number: "LOT-2026-051",
        title: "Granulation impeller speed exceeded the approved range",
      },
      message: "Updated the batch number and deviation title.",
      response: "Updated the batch number and deviation title.",
    });

    const { store } = renderWithStore();

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, {
      target: {
        value: "Change the batch to LOT-2026-051 and change the title to Granulation impeller speed exceeded the approved range.",
      },
    });

    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    await waitFor(() => {
      expect(screen.getByText("Updated the batch number and deviation title.")).toBeInTheDocument();
    });

    // Left form fields updated live in state
    expect(store.getState().deviations.form.batch_number).toBe("LOT-2026-051");
    expect(store.getState().deviations.form.title).toBe(
      "Granulation impeller speed exceeded the approved range"
    );
  });

  it("4. document upload: integrated into composer, runs pipeline, populates left form, and shows clean chat", async () => {
    api.extractDocument.mockResolvedValueOnce({
      success: true,
      source_type: "pdf",
      extracted_text: "Autoclave temperature excursion in batch LOT-2026-042",
      metadata: { filename: "deviation_report.pdf", page_count: 1 },
    });

    api.processDeviation.mockResolvedValueOnce({
      deviation: {
        site_plant: "Plant 1 - Sterile Ops",
        batch_lot_number: "LOT-2026-042",
        title_short_description: "Autoclave sterilization failure",
        detailed_description: "Temperature dropped to 118.5C for 20 minutes.",
        deviation_type: "equipment",
      },
      assessment: {
        recommended_severity: "critical",
        recommended_impact: "patient_safety",
        reason: "Direct sterility breach",
      },
    });

    const { store } = renderWithStore();

    const fileInput = document.getElementById("pdf-upload-input");
    expect(fileInput).not.toBeNull();

    const sampleFile = new File(["dummy pdf content"], "deviation_report.pdf", {
      type: "application/pdf",
    });

    // Trigger upload via file input (as triggered by attachment icon click)
    fireEvent.change(fileInput, { target: { files: [sampleFile] } });

    // 1. Chat displays user message "Uploaded deviation_report.pdf"
    expect(screen.getByText("Uploaded deviation_report.pdf")).toBeInTheDocument();

    // 2. Extraction pipeline runs
    await waitFor(() => {
      expect(api.extractDocument).toHaveBeenCalledWith(sampleFile);
      expect(api.processDeviation).toHaveBeenCalledWith(
        "Autoclave temperature excursion in batch LOT-2026-042",
        "pdf"
      );
    });

    // 3. AI responds in chat confirming extraction and form population
    await waitFor(() => {
      expect(
        screen.getByText(
          "I extracted the deviation details and populated the form. Please review the values on the left."
        )
      ).toBeInTheDocument();
    });

    // 4. Left form gets populated in Redux
    expect(store.getState().deviations.form.site_plant).toBe("Plant 1 - Sterile Ops");
    expect(store.getState().deviations.form.batch_number).toBe("LOT-2026-042");
    expect(store.getState().deviations.form.title).toBe("Autoclave sterilization failure");
    expect(store.getState().deviations.form.severity).toBe("critical");

    // 5. Right side contains ONLY chatbot (no large extraction cards or dropzone)
    expect(screen.queryByText(/Values Applied to Form/i)).toBeNull();
    expect(screen.queryByText(/DEVIATION SEVERITY REPORT/i)).toBeNull();
    expect(screen.queryByText(/Analysis Complete/i)).toBeNull();
  });

  it("5. manual edit and chat edit coexist cleanly", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "update_form",
      changes: {
        site_plant: "Demo Manufacturing Site",
      },
      message: "Updated Site / Plant to Demo Manufacturing Site.",
    });

    const { store } = renderWithStore();

    // 1. Manually edit description in Redux (user edit on left)
    store.dispatch(
      updateField({
        name: "description",
        value: "Manually entered description by the QA operator.",
      })
    );

    // 2. Chat modifies site
    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, { target: { value: "Set the site to Demo Manufacturing Site." } });
    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    await waitFor(() => {
      expect(screen.getByText("Updated Site / Plant to Demo Manufacturing Site.")).toBeInTheDocument();
    });

    // 3. Both changes coexist!
    expect(store.getState().deviations.form.description).toBe(
      "Manually entered description by the QA operator."
    );
    expect(store.getState().deviations.form.site_plant).toBe("Demo Manufacturing Site");
  });

  it("6. answers questions grounded in current deviation and form context", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "answer_question",
      message: "The current batch number is LOT-2026-051.",
      response: "The current batch number is LOT-2026-051.",
    });

    const preloadedState = {
      deviations: {
        form: {
          batch_number: "LOT-2026-051",
          site_plant: "Demo Manufacturing Site",
          severity: "critical",
        },
      },
      assistant: {
        extraction: { batch_number: "LOT-2026-051" },
        assessment: { recommended_severity: "critical" },
      },
    };

    renderWithStore(preloadedState);

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, { target: { value: "What is the current batch number?" } });
    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    await waitFor(() => {
      expect(api.sendDeviationChat).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "What is the current batch number?",
          currentForm: expect.objectContaining({ batch_number: "LOT-2026-051" }),
        })
      );
      expect(screen.getByText("The current batch number is LOT-2026-051.")).toBeInTheDocument();
    });
  });

  it("7. chat remains available after save and provides context of saved deviation", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "answer_question",
      message: "The AI recommended Critical severity due to direct sterility compromise.",
      response: "The AI recommended Critical severity due to direct sterility compromise.",
    });

    const preloadedState = {
      deviations: {
        form: {
          title: "Autoclave temperature drop",
          batch_number: "LOT-2026-051",
        },
        lastSaved: {
          reference: "DEV-2026-000042",
          status: "submitted",
          severity: "critical",
          ai_recommended_severity: "critical",
          ai_reason: "Direct sterility compromise",
        },
      },
    };

    renderWithStore(preloadedState);

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    expect(chatInput).not.toBeDisabled();

    fireEvent.change(chatInput, { target: { value: "What severity did the AI recommend?" } });
    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    await waitFor(() => {
      expect(api.sendDeviationChat).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "What severity did the AI recommend?",
          assessment: expect.objectContaining({ severity: "critical" }),
        })
      );
      expect(
        screen.getByText("The AI recommended Critical severity due to direct sterility compromise.")
      ).toBeInTheDocument();
    });
  });

  it("8. structured change display: single field change shows '✓ Change applied' and field details", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "update_form",
      changes: [
        {
          field: "title",
          label: "Title / Short Description",
          old_value: "Old generic title",
          new_value: "Granulation impeller speed exceeded the approved range",
        },
      ],
      message: "Change applied.",
    });

    const preloadedState = {
      deviations: {
        form: { title: "Old generic title" },
      },
    };

    const { store } = renderWithStore(preloadedState);

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, {
      target: { value: "Change the title to Granulation impeller speed exceeded the approved range." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    // 1. Verify structured confirmation header
    await waitFor(() => {
      expect(screen.getByText("Change applied")).toBeInTheDocument();
    });

    // 2. Verify field label and new value
    expect(screen.getByText("Title / Short Description")).toBeInTheDocument();
    expect(
      screen.getByText("Granulation impeller speed exceeded the approved range")
    ).toBeInTheDocument();

    // 3. Verify left form state simultaneously updated
    expect(store.getState().deviations.form.title).toBe(
      "Granulation impeller speed exceeded the approved range"
    );
  });

  it("9. structured change display: multiple fields show '✓ 3 changes applied' with audit-style values", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "update_form",
      changes: [
        {
          field: "site",
          label: "Site / Plant",
          old_value: "Plant 1",
          new_value: "Demo Manufacturing Site",
        },
        {
          field: "product_name",
          label: "Related Product / Material",
          old_value: "",
          new_value: "Paracetamol Tablets 500 mg",
        },
        {
          field: "batch_number",
          label: "Batch / Lot Number",
          old_value: "LOT-2026-042",
          new_value: "LOT-2026-051",
        },
      ],
      message: "3 changes applied.",
    });

    const preloadedState = {
      deviations: {
        form: {
          site_plant: "Plant 1",
          product_name: "",
          batch_number: "LOT-2026-042",
        },
      },
    };

    const { store } = renderWithStore(preloadedState);

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, {
      target: {
        value: "Set the site to Demo Manufacturing Site, product to Paracetamol Tablets 500 mg, and batch to LOT-2026-051.",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    // 1. Verify header
    await waitFor(() => {
      expect(screen.getByText("3 changes applied")).toBeInTheDocument();
    });

    // 2. Verify all labels and values
    expect(screen.getByText("Site / Plant")).toBeInTheDocument();
    expect(screen.getByText("Demo Manufacturing Site")).toBeInTheDocument();
    expect(screen.getByText("Related Product / Material")).toBeInTheDocument();
    expect(screen.getByText("Paracetamol Tablets 500 mg")).toBeInTheDocument();
    expect(screen.getByText("Batch / Lot Number")).toBeInTheDocument();
    expect(screen.getByText("LOT-2026-051")).toBeInTheDocument();

    // 3. Verify left form state updated simultaneously
    expect(store.getState().deviations.form.site_plant).toBe("Demo Manufacturing Site");
    expect(store.getState().deviations.form.product_name).toBe("Paracetamol Tablets 500 mg");
    expect(store.getState().deviations.form.batch_number).toBe("LOT-2026-051");
  });

  it("10. clarification request: ambiguous change does not modify form or show fake confirmation", async () => {
    api.sendDeviationChat.mockResolvedValueOnce({
      intent: "answer_question",
      changes: [],
      message:
        "I couldn't determine which form field you want to change. Please specify the information you want to update.",
    });

    const preloadedState = {
      deviations: {
        form: {
          site_plant: "Plant 1",
          batch_number: "LOT-2026-042",
        },
      },
    };

    const { store } = renderWithStore(preloadedState);

    const chatInput = screen.getByPlaceholderText(/Ask me anything about this deviation.../i);
    fireEvent.change(chatInput, { target: { value: "Change it" } });
    fireEvent.click(screen.getByRole("button", { name: /Send message/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          "I couldn't determine which form field you want to change. Please specify the information you want to update."
        )
      ).toBeInTheDocument();
    });

    // NO fake change confirmation
    expect(screen.queryByText(/Change applied/i)).toBeNull();
    expect(screen.queryByText(/changes applied/i)).toBeNull();

    // Form left intact
    expect(store.getState().deviations.form.site_plant).toBe("Plant 1");
    expect(store.getState().deviations.form.batch_number).toBe("LOT-2026-042");
  });
});

