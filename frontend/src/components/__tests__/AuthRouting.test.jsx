import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../../features/auth/authSlice.js";
import deviationReducer from "../../features/deviation/deviationSlice.js";
import deviationsReducer from "../../features/deviations/deviationsSlice.js";
import aiProcessingReducer from "../../features/ai/aiProcessingSlice.js";
import assessmentReducer from "../../features/assessment/assessmentSlice.js";
import uiReducer from "../../features/ui/uiSlice.js";
import assistantReducer from "../../features/assistant/assistantSlice.js";
import App from "../../App.jsx";
import LoginPage from "../LoginPage.jsx";
import { api } from "../../api/client.js";

// Mock API client
vi.mock("../../api/client.js", () => ({
  api: {
    login: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
    getDemoUsers: vi.fn().mockResolvedValue([
      {
        name: "Priyanshu",
        email: "priyanshu@gmail.com",
        company: "Vasundha Pharma Chem Limited",
        role: "QA Manager",
      },
    ]),
    listDeviations: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getReportSummary: vi.fn().mockResolvedValue({
      total: 0,
      by_severity: [],
      by_status: [],
      by_type: [],
    }),
  },
  API_BASE: "/api/v1",
}));

function createTestStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      auth: authReducer,
      deviation: deviationReducer,
      deviations: deviationsReducer,
      assistant: assistantReducer,
      aiProcessing: aiProcessingReducer,
      assessment: assessmentReducer,
      ui: uiReducer,
    },
    preloadedState,
  });
}

describe("Authentication & Routing Flows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  it("1. Unauthenticated user opening / is redirected to /login and sees Login page", async () => {
    window.history.replaceState({}, "", "/");
    const store = createTestStore({
      auth: {
        token: null,
        user: null,
        isAuthenticated: false,
        status: "idle",
        error: null,
      },
    });

    render(
      <Provider store={store}>
        <App />
      </Provider>
    );

    // Verify Login page is rendered
    expect(screen.getByText("PharmaOne-AI")).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Login$/i })).toBeInTheDocument();

    // Verify URL was redirected to /login
    expect(window.location.pathname).toBe("/login");
  });

  it("2. LoginPage displays demo login hint for priyanshu@gmail.com", () => {
    const store = createTestStore({
      auth: { isAuthenticated: false },
    });

    render(
      <Provider store={store}>
        <LoginPage />
      </Provider>
    );

    expect(screen.getByText(/Demo Login:/i)).toBeInTheDocument();
    expect(screen.getByText("priyanshu@gmail.com")).toBeInTheDocument();
  });

  it("3. Unauthenticated user attempting to visit /dashboard is redirected to /login", async () => {
    window.history.replaceState({}, "", "/dashboard");
    const store = createTestStore({
      auth: { isAuthenticated: false },
    });

    render(
      <Provider store={store}>
        <App />
      </Provider>
    );

    expect(screen.getByText("PharmaOne-AI")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });

  it("4. Authenticated user visiting / or /login is redirected to /dashboard", async () => {
    const mockUser = {
      id: "u-1",
      email: "priyanshu@gmail.com",
      full_name: "Priyanshu",
      role: "QA Manager",
      company_name: "Vasundha Pharma Chem Limited",
    };
    api.me.mockResolvedValue(mockUser);
    localStorage.setItem("pharmaone_auth_token", "fake-jwt-token");
    localStorage.setItem("pharmaone_auth_user", JSON.stringify(mockUser));

    window.history.replaceState({}, "", "/login");
    const store = createTestStore({
      auth: {
        token: "fake-jwt-token",
        user: mockUser,
        isAuthenticated: true,
      },
    });

    render(
      <Provider store={store}>
        <App />
      </Provider>
    );

    await waitFor(() => {
      expect(window.location.pathname).toBe("/dashboard");
    });
    expect(screen.getByText("Total Deviations")).toBeInTheDocument();
  });

  it("5. Login form submits with priyanshu@gmail.com and password", async () => {
    api.login.mockResolvedValueOnce({
      access_token: "mock-priyanshu-token",
      user: {
        id: "cad0002e-03df-4110-9673-ee7bdabeb9a5",
        email: "priyanshu@gmail.com",
        full_name: "Priyanshu",
        role: "QA Manager",
        company_name: "Vasundha Pharma Chem Limited",
      },
    });

    const store = createTestStore({
      auth: {
        token: null,
        user: null,
        isAuthenticated: false,
        status: "idle",
        error: null,
      },
    });

    render(
      <Provider store={store}>
        <LoginPage />
      </Provider>
    );

    const emailInput = screen.getByLabelText(/Email/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    const loginButton = screen.getByRole("button", { name: /^Login$/i });

    expect(emailInput.value).toBe("priyanshu@gmail.com");
    expect(passwordInput.value).toBe("123456789");

    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith({
        email: "priyanshu@gmail.com",
        password: "123456789",
      });
    });
  });

  it("6. Logout clears credentials and redirects to /login", async () => {
    const mockUser = {
      email: "priyanshu@gmail.com",
      full_name: "Priyanshu",
      role: "QA Manager",
      company_name: "Vasundha Pharma Chem Limited",
    };
    api.logout.mockResolvedValueOnce({ status: "ok" });
    api.me.mockResolvedValue(mockUser);
    localStorage.setItem("pharmaone_auth_token", "fake-token");
    localStorage.setItem(
      "pharmaone_auth_user",
      JSON.stringify(mockUser)
    );

    window.history.replaceState({}, "", "/dashboard");
    const store = createTestStore({
      auth: {
        token: "fake-token",
        user: mockUser,
        isAuthenticated: true,
      },
    });

    render(
      <Provider store={store}>
        <App />
      </Provider>
    );

    // Click user avatar to open dropdown
    const userMenuButton = screen.getByRole("button", { name: /Priyanshu/i });
    fireEvent.click(userMenuButton);

    // Click Sign Out
    const signOutBtn = screen.getByRole("button", { name: /Sign Out/i });
    fireEvent.click(signOutBtn);

    await waitFor(() => {
      expect(screen.getByText("PharmaOne-AI")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/login");
    });
  });
});
