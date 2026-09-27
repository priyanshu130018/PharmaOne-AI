import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import deviationsReducer from "../../features/deviations/deviationsSlice.js";
import authReducer from "../../features/auth/authSlice.js";
import DashboardView from "../DashboardView.jsx";

function renderWithStore(preloadedState = {}, props = {}) {
  const store = configureStore({
    reducer: {
      deviations: deviationsReducer,
      auth: authReducer,
    },
    preloadedState,
  });

  const utils = render(
    <Provider store={store}>
      <DashboardView {...props} />
    </Provider>
  );

  return { store, ...utils };
}

describe("DashboardView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders empty state properly when no deviations exist", () => {
    const onNavigate = vi.fn();
    renderWithStore(
      {
        auth: {
          user: { company_name: "Vasundha Pharma Chem Limited" },
        },
        deviations: {
          summary: { total: 0, by_severity: [], by_status: [], by_type: [] },
          list: [],
        },
      },
      { onNavigateToLogDeviation: onNavigate }
    );

    // Verify company name banner
    expect(screen.getByText("Vasundha Pharma Chem Limited")).toBeInTheDocument();
    expect(screen.getByText("Overview of deviation activity and items requiring attention")).toBeInTheDocument();

    // Verify summary counts
    expect(screen.getByText("Total Deviations")).toBeInTheDocument();
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(1);

    // Verify empty states
    expect(screen.getByText("No deviations recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("No deviations currently require review.")).toBeInTheDocument();
    expect(
      screen.getByText("No activity recorded yet. Quality trends will be calculated automatically as records are logged.")
    ).toBeInTheDocument();

    // Verify Log Deviation button
    const logBtns = screen.getAllByRole("button", { name: /Log Deviation/i });
    expect(logBtns.length).toBeGreaterThanOrEqual(1);
    fireEvent.click(logBtns[0]);
    expect(onNavigate).toHaveBeenCalled();
  });

  it("2. renders real data with recent deviations and items requiring review", () => {
    renderWithStore({
      auth: {
        user: { company_name: "Vasundha Pharma Chem Limited" },
      },
      deviations: {
        summary: {
          total: 2,
          by_severity: [
            { key: "critical", count: 1 },
            { key: "major", count: 1 },
          ],
          by_status: [
            { key: "submitted", count: 1 },
            { key: "closed", count: 1 },
          ],
          by_type: [
            { key: "equipment", count: 1 },
            { key: "process", count: 1 },
          ],
        },
        list: [
          {
            id: "dev-1",
            reference: "DEV-2026-000001",
            title: "Autoclave Sterility Excursion",
            severity: "critical",
            status: "submitted", // requires review
            occurred_on: "2026-03-25",
            created_at: "2026-03-25T10:00:00Z",
          },
          {
            id: "dev-2",
            reference: "DEV-2026-000002",
            title: "Packaging Label Misalignment",
            severity: "major",
            status: "closed", // does not require review
            occurred_on: "2026-03-26",
            created_at: "2026-03-26T11:00:00Z",
          },
        ],
      },
    });

    // Check KPI counts
    expect(screen.getByText("Total Deviations")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();

    // Check recent deviations table shows both
    expect(screen.getAllByText("DEV-2026-000001").length).toBe(2);
    expect(screen.getByText("DEV-2026-000002")).toBeInTheDocument();
    expect(screen.getAllByText("Autoclave Sterility Excursion").length).toBe(2);
    expect(screen.getByText("Packaging Label Misalignment")).toBeInTheDocument();

    // Check review required list contains dev-1 (status !== 'closed')
    expect(screen.getByText("1 pending")).toBeInTheDocument();

    // Check deviation activity sections
    expect(screen.getByText("Activity by Deviation Type")).toBeInTheDocument();
    expect(screen.getByText("Activity by Lifecycle Status")).toBeInTheDocument();
  });
});
