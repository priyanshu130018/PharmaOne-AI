import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import assistantReducer from "../../features/assistant/assistantSlice.js";
import deviationsReducer from "../../features/deviations/deviationsSlice.js";
import AiAssistantPanel from "../AiAssistantPanel.jsx";
import { api } from "../../api/client.js";

// Mock API client methods
vi.mock("../../api/client.js", () => ({
  api: {
    extractDocument: vi.fn(),
    extractText: vi.fn(),
    processDeviation: vi.fn(),
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

describe("AiAssistantPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. upload: handles file selection and triggers document extraction pipeline", async () => {
    api.extractDocument.mockResolvedValueOnce({
      success: true,
      source_type: "pdf",
      extracted_text: "Sterility test failure in batch B-42",
      metadata: {
        filename: "deviation.pdf",
        page_count: 1,
        character_count: 36,
        ocr_applied: false,
      },
    });

    api.processDeviation.mockResolvedValueOnce({
      extraction: {
        title: "Sterility test failure",
        batch_number: "B-42",
      },
      assessment: {
        recommended_severity: "critical",
        recommended_impact: "patient_safety",
        reason: "Microbial risk",
      },
    });

    renderWithStore();

    // Verify upload mode tab is active
    expect(screen.getByText(/Upload PDF \/ Document/i)).toBeInTheDocument();

    const fileInput = document.getElementById("pdf-upload-input");
    expect(fileInput).not.toBeNull();

    // Select file
    const file = new File(["test-content"], "deviation.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // File card should appear
    expect(screen.getByText("deviation.pdf")).toBeInTheDocument();

    // Click Analyze Document
    const analyzeBtn = screen.getByRole("button", { name: /Analyze Document/i });
    expect(analyzeBtn).not.toBeDisabled();
    fireEvent.click(analyzeBtn);

    // Verify API called
    await waitFor(() => {
      expect(api.extractDocument).toHaveBeenCalledWith(file);
      expect(api.processDeviation).toHaveBeenCalledWith(
        "Sterility test failure in batch B-42",
        "pdf"
      );
    });

    // Check success indication
    await waitFor(() => {
      expect(
        screen.getByText(/Extracted fields automatically populated into deviation form/i)
      ).toBeInTheDocument();
    });
  });

  it("2. paste text: switches mode, accepts pasted text, and triggers text extraction", async () => {
    api.extractText.mockResolvedValueOnce({
      success: true,
      source_type: "text",
      extracted_text: "Autoclave pressure excursion during sterilization cycle.",
      metadata: {
        character_count: 55,
        page_count: 1,
      },
    });

    api.processDeviation.mockResolvedValueOnce({
      extraction: {
        title: "Autoclave pressure excursion",
        equipment: "Autoclave",
      },
      assessment: {
        recommended_severity: "major",
        recommended_impact: "product_quality",
        reason: "Sterilization cycle deviation",
      },
    });

    renderWithStore();

    // Switch to paste tab
    const pasteTab = screen.getByText(/Paste Text \/ Email/i);
    fireEvent.click(pasteTab);

    // Type text into textarea
    const textarea = screen.getByPlaceholderText(/Paste deviation description/i);
    fireEvent.change(textarea, {
      target: { value: "Autoclave pressure excursion during sterilization cycle." },
    });

    // Click Analyze Text
    const analyzeBtn = screen.getByRole("button", { name: /Analyze Text/i });
    expect(analyzeBtn).not.toBeDisabled();
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(api.extractText).toHaveBeenCalledWith(
        "Autoclave pressure excursion during sterilization cycle.",
        "text"
      );
      expect(api.processDeviation).toHaveBeenCalled();
    });
  });

  it("3. loading: displays active progress stages and disables submit during processing", async () => {
    // Return promise that stays unresolved for a short duration
    let resolveExtraction;
    const extractionPromise = new Promise((resolve) => {
      resolveExtraction = resolve;
    });

    api.extractDocument.mockReturnValue(extractionPromise);

    renderWithStore();

    const fileInput = document.getElementById("pdf-upload-input");
    const file = new File(["dummy"], "report.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const analyzeBtn = screen.getByRole("button", { name: /Analyze Document/i });
    fireEvent.click(analyzeBtn);

    // Verify loading state
    expect(screen.getByText(/Processing…/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Extracting text/i).length).toBeGreaterThanOrEqual(1);
    expect(analyzeBtn).toBeDisabled();

    // Resolve promise and await resolution
    await act(async () => {
      resolveExtraction({
        success: true,
        source_type: "pdf",
        extracted_text: "Clean text",
        metadata: {},
      });
    });
  });

  it("4. error: displays structured error message when extraction fails", async () => {
    api.extractDocument.mockRejectedValueOnce(
      new Error("The document appears to be a scanned image and OCR is unavailable.")
    );

    renderWithStore();

    const fileInput = document.getElementById("pdf-upload-input");
    const file = new File(["dummy"], "scanned.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const analyzeBtn = screen.getByRole("button", { name: /Analyze Document/i });
    fireEvent.click(analyzeBtn);

    // Verify error state
    await waitFor(() => {
      expect(screen.getByText(/Processing Error/i)).toBeInTheDocument();
      expect(
        screen.getByText(/The document appears to be a scanned image and OCR is unavailable/i)
      ).toBeInTheDocument();
    });
  });

  it("5. retry: enables one-click retry on failure and re-executes the operation", async () => {
    // First attempt fails
    api.extractDocument.mockRejectedValueOnce(new Error("Network timeout during upload"));

    // Second attempt succeeds
    api.extractDocument.mockResolvedValueOnce({
      success: true,
      source_type: "pdf",
      extracted_text: "Retry succeeded text",
      metadata: { page_count: 1, character_count: 20 },
    });

    api.processDeviation.mockResolvedValueOnce({
      extraction: { title: "Retry succeeded" },
      assessment: { recommended_severity: "minor", recommended_impact: "none", reason: "Ok" },
    });

    renderWithStore();

    const fileInput = document.getElementById("pdf-upload-input");
    const file = new File(["dummy"], "retry_doc.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const analyzeBtn = screen.getByRole("button", { name: /Analyze Document/i });
    fireEvent.click(analyzeBtn);

    // Wait for first attempt to fail and show retry button
    const retryBtn = await screen.findByRole("button", { name: /Retry/i });
    expect(retryBtn).toBeInTheDocument();
    expect(screen.getByText(/Network timeout during upload/i)).toBeInTheDocument();

    // Click retry
    fireEvent.click(retryBtn);

    // Verify second attempt was initiated
    await waitFor(() => {
      expect(api.extractDocument).toHaveBeenCalledTimes(2);
      expect(screen.getByText(/Retry succeeded text/i)).toBeInTheDocument();
    });
  });
});
