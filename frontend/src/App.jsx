import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Header from "./components/Header.jsx";
import LogDeviationForm from "./components/LogDeviationForm.jsx";
import AiAssistantPanel from "./components/AiAssistantPanel.jsx";
import DashboardView from "./components/DashboardView.jsx";
import LoginPage from "./components/LoginPage.jsx";
import { restoreSession } from "./features/auth/authSlice.js";
import { fetchDeviations, fetchSummary } from "./features/deviations/deviationsSlice.js";

export default function App() {
  const dispatch = useDispatch();
  const { isAuthenticated, user } = useSelector((s) => s.auth);

  const getInitialView = () => {
    if (typeof window !== "undefined") {
      const path = window.location.pathname.toLowerCase();
      if (path.startsWith("/deviations")) return "deviations";
      return "dashboard";
    }
    return "dashboard";
  };

  const [activeView, setActiveView] = useState(getInitialView);
  const [toastMessage, setToastMessage] = useState(null);

  const handleViewChange = (view) => {
    setActiveView(view);
    if (typeof window !== "undefined") {
      const targetPath = view === "dashboard" ? "/dashboard" : "/deviations";
      if (window.location.pathname !== targetPath) {
        window.history.pushState({}, "", targetPath);
      }
    }
  };

  // Synchronize URL and routing state on mount and auth changes
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (!isAuthenticated) {
      if (window.location.pathname !== "/login") {
        window.history.replaceState({}, "", "/login");
      }
    } else {
      const path = window.location.pathname.toLowerCase();
      if (path === "/" || path === "/login" || path === "") {
        window.history.replaceState({}, "", "/dashboard");
        setActiveView("dashboard");
      }
    }
  }, [isAuthenticated]);

  // Handle browser back / forward navigation
  useEffect(() => {
    const handlePopState = () => {
      if (typeof window === "undefined") return;
      const path = window.location.pathname.toLowerCase();

      if (!isAuthenticated) {
        if (path !== "/login") {
          window.history.replaceState({}, "", "/login");
        }
        return;
      }

      if (path === "/" || path === "/login") {
        window.history.replaceState({}, "", "/dashboard");
        setActiveView("dashboard");
      } else if (path.startsWith("/dashboard")) {
        setActiveView("dashboard");
      } else if (path.startsWith("/deviations")) {
        setActiveView("deviations");
      } else {
        window.history.replaceState({}, "", "/dashboard");
        setActiveView("dashboard");
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [isAuthenticated]);

  // Attempt to restore existing session on page load
  useEffect(() => {
    dispatch(restoreSession());
  }, [dispatch]);

  // Fetch initial deviation list and report summary once authenticated
  useEffect(() => {
    if (isAuthenticated) {
      dispatch(fetchDeviations());
      dispatch(fetchSummary());
    }
  }, [dispatch, isAuthenticated]);

  const showToast = (message) => {
    setToastMessage(message);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // If user is not authenticated, strictly render LoginPage
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-800 font-sans antialiased">
      {/* Top Application Header */}
      <Header
        activeView={activeView}
        onViewChange={handleViewChange}
        onShowToast={showToast}
      />

      {/* Main Workspace Body */}
      {activeView === "deviations" && (
        <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 sm:px-6 lg:px-8 py-4">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            <div className="lg:col-span-7 lg:h-[calc(100vh-6.25rem)] min-h-[640px]">
              <LogDeviationForm />
            </div>
            <div className="lg:col-span-5 lg:h-[calc(100vh-6.25rem)] min-h-[640px]">
              <AiAssistantPanel />
            </div>
          </div>
        </main>
      )}

      {activeView === "dashboard" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <DashboardView onNavigateToLogDeviation={() => handleViewChange("deviations")} />
        </main>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-2.5 text-center text-xs text-slate-400">
        PharmaOne-AI · Enterprise Deviation Intake & Quality Management · AI output is decision support and requires human verification.
      </footer>

      {/* Non-intrusive Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-xs text-white shadow-lg animate-fade-in"
        >
          <svg className="h-4 w-4 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{toastMessage}</span>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="ml-2 text-slate-400 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
