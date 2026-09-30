import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Header from "./components/Header.jsx";
import LogDeviationForm from "./components/LogDeviationForm.jsx";
import AiAssistantPanel from "./components/AiAssistantPanel.jsx";
import DashboardView from "./components/DashboardView.jsx";
import LoginPage from "./components/LoginPage.jsx";
import BatchModuleView from "./components/BatchModuleView.jsx";
import InvestigationWorkspaceView from "./components/InvestigationWorkspaceView.jsx";
import RootCauseView from "./components/RootCauseView.jsx";
import CapaWorkspaceView from "./components/CapaWorkspaceView.jsx";
import EffectivenessView from "./components/EffectivenessView.jsx";
import ClosureView from "./components/ClosureView.jsx";
import BatchReleaseView from "./components/BatchReleaseView.jsx";
import ComplaintView from "./components/ComplaintView.jsx";
import SupplierView from "./components/SupplierView.jsx";
import AuditTrailView from "./components/AuditTrailView.jsx";

import { restoreSession } from "./features/auth/authSlice.js";
import { fetchDeviations, fetchSummary, prefillFromIpc } from "./features/deviations/deviationsSlice.js";

export default function App() {
  const dispatch = useDispatch();
  const { isAuthenticated, user } = useSelector((s) => s.auth);

  const getInitialView = () => {
    if (typeof window !== "undefined") {
      const path = window.location.pathname.toLowerCase();
      if (path.startsWith("/deviations")) return "deviations";
      if (path.startsWith("/batches")) return "batches";
      if (path.startsWith("/investigation")) return "investigation";
      if (path.startsWith("/root_cause")) return "root_cause";
      if (path.startsWith("/capa")) return "capa";
      if (path.startsWith("/effectiveness")) return "effectiveness";
      if (path.startsWith("/closure")) return "closure";
      if (path.startsWith("/batch_release") || path.startsWith("/release")) return "batch_release";
      if (path.startsWith("/complaints")) return "complaints";
      if (path.startsWith("/suppliers")) return "suppliers";
      if (path.startsWith("/audit")) return "audit_trail";
      return "dashboard";
    }
    return "dashboard";
  };

  const [activeView, setActiveView] = useState(getInitialView);
  const [navParams, setNavParams] = useState({
    batchNumber: "API-2026-041",
    deviationId: "DEV-2026-018",
    investigationId: "INV-2026-012",
    capaId: "CAPA-2026-009",
    batchReleaseId: "BR-2026-041"
  });
  const [toastMessage, setToastMessage] = useState(null);

  const handleViewChange = (view) => {
    setActiveView(view);
    if (typeof window !== "undefined") {
      const targetPath = view === "dashboard" ? "/dashboard" : `/${view}`;
      if (window.location.pathname !== targetPath) {
        window.history.pushState({ view }, "", targetPath);
      }
    }
  };

  const handleCustomNavigate = (view, params = {}) => {
    setNavParams((prev) => ({ ...prev, ...params }));
    setActiveView(view);
    if (typeof window !== "undefined") {
      const targetPath = view === "dashboard" ? "/dashboard" : `/${view}`;
      if (window.location.pathname !== targetPath) {
        window.history.pushState({ view, params }, "", targetPath);
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleCreateDeviationFromIpc = (ipcData) => {
    if (ipcData?.batch_number) {
      setNavParams((prev) => ({ ...prev, batchNumber: ipcData.batch_number }));
    }
    dispatch(prefillFromIpc(ipcData));
    handleViewChange("deviations");
    showToast(`Pre-populated deviation intake for Batch ${ipcData.batch_number || ''} (${ipcData.parameter || 'IPC'}: ${ipcData.actual_condition || 'Excursion'})`);
  };

  const handleRecordClick = (type, id) => {
    if (type === "batch") {
      handleCustomNavigate("batches", { batchNumber: id || "API-2026-041" });
    } else if (type === "ipc") {
      handleCustomNavigate("batches", { batchNumber: "API-2026-041" });
    } else if (type === "deviation") {
      handleCustomNavigate("deviations", { deviationId: id || "DEV-2026-018" });
    } else if (type === "investigation") {
      handleCustomNavigate("investigation", { investigationId: id || "INV-2026-012", deviationId: "DEV-2026-018" });
    } else if (type === "root_cause") {
      handleCustomNavigate("root_cause", { investigationId: id || "INV-2026-012", deviationId: "DEV-2026-018" });
    } else if (type === "capa") {
      handleCustomNavigate("capa", { capaId: id || "CAPA-2026-009", deviationId: "DEV-2026-018" });
    } else if (type === "effectiveness") {
      handleCustomNavigate("effectiveness", { capaId: id || "CAPA-2026-009", deviationId: "DEV-2026-018" });
    } else if (type === "closed" || type === "closure") {
      handleCustomNavigate("closure", { deviationId: id || "DEV-2026-018" });
    } else if (type === "batch_release") {
      handleCustomNavigate("batch_release", { batchNumber: "API-2026-041", batchReleaseId: id || "BR-2026-041" });
    } else if (type === "complaint") {
      handleCustomNavigate("complaints", { complaintNumber: id });
    } else if (type === "supplier" || type === "raw_material") {
      handleCustomNavigate("batches", {});
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

      if (path === "/" || path === "/login" || path.startsWith("/dashboard")) {
        window.history.replaceState({}, "", "/dashboard");
        setActiveView("dashboard");
      } else if (path.startsWith("/deviations")) {
        setActiveView("deviations");
      } else if (path.startsWith("/batches")) {
        setActiveView("batches");
      } else if (path.startsWith("/investigation")) {
        setActiveView("investigation");
      } else if (path.startsWith("/root_cause")) {
        setActiveView("root_cause");
      } else if (path.startsWith("/capa")) {
        setActiveView("capa");
      } else if (path.startsWith("/effectiveness")) {
        setActiveView("effectiveness");
      } else if (path.startsWith("/closure")) {
        setActiveView("closure");
      } else if (path.startsWith("/batch_release") || path.startsWith("/release")) {
        setActiveView("batch_release");
      } else if (path.startsWith("/complaints")) {
        setActiveView("complaints");
      } else if (path.startsWith("/suppliers")) {
        setActiveView("suppliers");
      } else if (path.startsWith("/audit")) {
        setActiveView("audit_trail");
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
      {activeView === "dashboard" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <DashboardView 
            onNavigateToLogDeviation={() => handleViewChange("deviations")} 
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "deviations" && (
        <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 sm:px-6 lg:px-8 py-4">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            <div className="lg:col-span-7 lg:h-[calc(100vh-6.25rem)] min-h-[640px]">
              <LogDeviationForm 
                onNavigate={handleCustomNavigate} 
                onRecordClick={handleRecordClick} 
              />
            </div>
            <div className="lg:col-span-5 lg:h-[calc(100vh-6.25rem)] min-h-[640px]">
              <AiAssistantPanel />
            </div>
          </div>
        </main>
      )}

      {activeView === "batches" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <BatchModuleView 
            batchNumber={navParams.batchNumber || "API-2026-041"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
            onCreateDeviationFromIpc={handleCreateDeviationFromIpc}
          />
        </main>
      )}

      {activeView === "raw_materials" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <SupplierView 
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "process_checks" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <BatchModuleView 
            batchNumber={navParams.batchNumber || "API-2026-041"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
            onCreateDeviationFromIpc={handleCreateDeviationFromIpc}
          />
        </main>
      )}

      {activeView === "investigation" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <InvestigationWorkspaceView 
            investigationId={navParams.investigationId || "INV-2026-012"}
            deviationId={navParams.deviationId || "DEV-2026-018"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "root_cause" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <RootCauseView 
            investigationId={navParams.investigationId || "INV-2026-012"}
            deviationId={navParams.deviationId || "DEV-2026-018"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "capa" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <CapaWorkspaceView 
            capaId={navParams.capaId || "CAPA-2026-009"}
            deviationId={navParams.deviationId || "DEV-2026-018"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "effectiveness" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <EffectivenessView 
            capaId={navParams.capaId || "CAPA-2026-009"}
            deviationId={navParams.deviationId || "DEV-2026-018"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "closure" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <ClosureView 
            deviationId={navParams.deviationId || "DEV-2026-018"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "batch_release" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <BatchReleaseView 
            batchNumber={navParams.batchNumber || "API-2026-041"}
            batchReleaseId={navParams.batchReleaseId || "BR-2026-041"}
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "complaints" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <ComplaintView 
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "suppliers" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <SupplierView 
            onNavigate={handleCustomNavigate}
            onRecordClick={handleRecordClick}
          />
        </main>
      )}

      {activeView === "audit_trail" && (
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6">
          <AuditTrailView onRecordClick={handleRecordClick} />
        </main>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-2.5 text-center text-xs text-slate-400">
        PharmaOne-AI · Enterprise Pharmaceutical Quality Management System (QMS) · 21 CFR Part 11 Compliant · AI Advisory Decision Support with QA Human Verification.
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
