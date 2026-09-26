import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import Header from "./components/Header.jsx";
import LogDeviationForm from "./components/LogDeviationForm.jsx";
import AiAssistantPanel from "./components/AiAssistantPanel.jsx";
import RecentDeviations from "./components/RecentDeviations.jsx";
import { fetchDeviations, fetchSummary } from "./features/deviations/deviationsSlice.js";

export default function App() {
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(fetchDeviations());
    dispatch(fetchSummary());
  }, [dispatch]);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="lg:h-[calc(100vh-11rem)]">
            <LogDeviationForm />
          </div>
          <div className="lg:h-[calc(100vh-11rem)]">
            <AiAssistantPanel />
          </div>
        </div>
        <div className="mt-6">
          <RecentDeviations />
        </div>
      </main>
      <footer className="border-t border-slate-200 bg-white py-3 text-center text-xs text-slate-400">
        PharmaOne AI · Deviation Intake foundation · AI output is decision support and
        requires human review.
      </footer>
    </div>
  );
}
