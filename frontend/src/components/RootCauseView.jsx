import React, { useState, useEffect } from 'react';
import { 
  GitBranch, Sparkles, CheckCircle2, AlertTriangle, ArrowRight, 
  RefreshCw, Check, X, ShieldAlert, Edit3, Save, Layers, HelpCircle
} from './icons.jsx';
import { 
  getInvestigation, 
  saveInvestigationRootCause, 
  aiGenerate5Whys,
  getDeviationLinkedRecords,
  createCapa
} from '../api/client';
import LinkedRecordsBar from './LinkedRecordsBar';
import WorkflowStepper from './WorkflowStepper';

export default function RootCauseView({ 
  investigationId = 'INV-2026-012', 
  deviationId = 'DEV-2026-018',
  onNavigate,
  onRecordClick 
}) {
  const [investigation, setInvestigation] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 5 Whys Form State
  const [problemStatement, setProblemStatement] = useState('Temperature reached 84 °C.');
  const [why1, setWhy1] = useState('Cooling response was delayed.');
  const [why2, setWhy2] = useState('Cooling valve did not respond correctly.');
  const [why3, setWhy3] = useState('Valve actuator malfunctioned.');
  const [why4, setWhy4] = useState('Maintenance did not detect actuator degradation.');
  const [why5, setWhy5] = useState('Preventive maintenance controls did not adequately cover actuator degradation.');
  const [finalRootCause, setFinalRootCause] = useState('Inadequate preventive-maintenance control for the cooling-valve actuator.');
  const [contributingFactors, setContributingFactors] = useState(['High duty cycle', 'Missing calibration check on actuator positioner']);
  const [newFactorInput, setNewFactorInput] = useState('');
  
  // Explicit human confirmation
  const [humanConfirmed, setHumanConfirmed] = useState(true);
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // AI Generation State
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiDraft, setAiDraft] = useState(null);
  const [showAiModal, setShowAiModal] = useState(false);

  // CAPA Creation Modal
  const [showCreateCapaModal, setShowCreateCapaModal] = useState(false);
  const [capaTitle, setCapaTitle] = useState('Preventive Maintenance Enhancement for Reactor Cooling Valve Actuators');
  const [capaType, setCapaType] = useState('Both');
  const [capaOwner, setCapaOwner] = useState('Engineering');
  const [isSubmittingCapa, setIsSubmittingCapa] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const invData = await getInvestigation(investigationId);
      setInvestigation(invData);

      const rca = invData.root_cause || invData.root_cause_analysis;
      if (rca) {
        if (rca.problem_statement) setProblemStatement(rca.problem_statement);
        if (rca.why_1) setWhy1(rca.why_1);
        if (rca.why_2) setWhy2(rca.why_2);
        if (rca.why_3) setWhy3(rca.why_3);
        if (rca.why_4) setWhy4(rca.why_4);
        if (rca.why_5) setWhy5(rca.why_5);
        if (rca.final_root_cause || rca.root_cause_summary) setFinalRootCause(rca.final_root_cause || rca.root_cause_summary);
        if (rca.contributing_factors) {
          if (Array.isArray(rca.contributing_factors)) {
            setContributingFactors(rca.contributing_factors);
          } else if (typeof rca.contributing_factors === 'string') {
            try {
              const parsed = JSON.parse(rca.contributing_factors);
              if (Array.isArray(parsed)) setContributingFactors(parsed);
              else setContributingFactors([rca.contributing_factors]);
            } catch {
              setContributingFactors(rca.contributing_factors.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean));
            }
          }
        }
        setIsSaved(true);
        if (rca.human_confirmed) setHumanConfirmed(true);
      }

      const devTarget = invData.deviation_id || deviationId;
      if (devTarget) {
        try {
          const links = await getDeviationLinkedRecords(devTarget);
          setLinkedRecords(links);
        } catch (e) {
          console.warn('Could not fetch linked records', e);
        }
      }
    } catch (err) {
      console.error('Failed to load RCA details:', err);
      setError(err.message || 'Failed to load root cause record.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [investigationId]);

  const handleGenerateAi = async () => {
    try {
      setIsAiLoading(true);
      const res = await aiGenerate5Whys(investigation.id, investigation.deviation_id || deviationId);
      setAiDraft(res);
      setShowAiModal(true);
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to generate 5 Whys draft: ' + err.message });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleAcceptAiDraft = () => {
    if (!aiDraft) return;
    if (aiDraft.problem_statement) setProblemStatement(aiDraft.problem_statement);
    if (aiDraft.why_1) setWhy1(aiDraft.why_1);
    if (aiDraft.why_2) setWhy2(aiDraft.why_2);
    if (aiDraft.why_3) setWhy3(aiDraft.why_3);
    if (aiDraft.why_4) setWhy4(aiDraft.why_4);
    if (aiDraft.why_5) setWhy5(aiDraft.why_5);
    if (aiDraft.final_root_cause) setFinalRootCause(aiDraft.final_root_cause);
    if (aiDraft.contributing_factors && Array.isArray(aiDraft.contributing_factors)) {
      setContributingFactors(aiDraft.contributing_factors);
    }
    setHumanConfirmed(true);
    setShowAiModal(false);
    setFeedback({ type: 'success', message: 'AI 5-Whys draft successfully loaded into RCA workspace.' });
  };

  const handleSaveRootCause = async () => {
    if (!finalRootCause.trim()) {
      setFeedback({ type: 'error', message: 'Final Root Cause statement cannot be empty.' });
      return;
    }
    if (!humanConfirmed) {
      setFeedback({ type: 'error', message: 'You must check the QA/Investigator confirmation box to officially authorize this Root Cause.' });
      return;
    }

    try {
      setIsSaving(true);
      await saveInvestigationRootCause(investigation.id, {
        problem_statement: problemStatement,
        why_1: why1,
        why_2: why2,
        why_3: why3,
        why_4: why4,
        why_5: why5,
        final_root_cause: finalRootCause,
        root_cause_summary: finalRootCause,
        contributing_factors: contributingFactors,
        human_confirmed: true
      });
      setIsSaved(true);
      setFeedback({ type: 'success', message: 'Root Cause Analysis successfully saved and confirmed.' });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to save root cause: ' + err.message });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateCapaSubmit = async (e) => {
    e.preventDefault();
    try {
      setIsSubmittingCapa(true);
      const capa = await createCapa({
        deviation_id: investigation.deviation_id || deviationId,
        investigation_id: investigation.id,
        title: capaTitle,
        capa_type: capaType,
        assigned_owner: capaOwner,
        root_cause_summary: finalRootCause
      });
      setShowCreateCapaModal(false);
      onNavigate?.('capa', { deviationId, capaId: capa.capa_number || 'CAPA-2026-009' });
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to create CAPA: ' + err.message });
    } finally {
      setIsSubmittingCapa(false);
    }
  };

  const addContributingFactor = () => {
    if (!newFactorInput.trim()) return;
    setContributingFactors([...contributingFactors, newFactorInput.trim()]);
    setNewFactorInput('');
  };

  const removeContributingFactor = (idx) => {
    setContributingFactors(contributingFactors.filter((_, i) => i !== idx));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-slate-600 font-medium">Loading Root Cause Analysis...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Linked Records Bar */}
      <LinkedRecordsBar 
        records={linkedRecords}
        activeType="root_cause"
        onRecordClick={onRecordClick}
      />

      {/* Feedback Notification Banner */}
      {feedback && (
        <div className={`p-4 rounded-xl border text-xs flex items-center justify-between shadow-xs transition-all ${
          feedback.type === 'error'
            ? 'bg-red-50 text-red-800 border-red-200'
            : feedback.type === 'info'
            ? 'bg-blue-50 text-blue-800 border-blue-200'
            : 'bg-emerald-50 text-emerald-800 border-emerald-200'
        }`}>
          <div className="flex items-center gap-2">
            {feedback.type === 'error' ? (
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
            ) : (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            )}
            <span className="font-semibold">{feedback.message}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-600 font-bold ml-3">✕</button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-3">
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-indigo-100 text-indigo-800 flex items-center gap-1.5">
              <GitBranch className="w-3.5 h-3.5" />
              Root Cause Analysis (5 Whys)
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded ${
              isSaved ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {isSaved ? 'Root Cause Confirmed' : 'Draft In Progress'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">
            RCA: Reactor Temperature Excursion (84 °C)
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Linked Investigation: <button onClick={() => onRecordClick?.('investigation', investigationId)} className="text-blue-600 font-medium hover:underline">{investigationId}</button>
            {' • '}Deviation: <button onClick={() => onRecordClick?.('deviation', deviationId)} className="text-blue-600 font-medium hover:underline">{deviationId}</button>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerateAi}
            disabled={isAiLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition shadow-sm"
          >
            <Sparkles className={`w-4 h-4 ${isAiLoading ? 'animate-spin' : 'text-indigo-600'}`} />
            {isAiLoading ? 'Synthesizing...' : 'Generate 5 Whys (AI)'}
          </button>

          <button
            onClick={handleSaveRootCause}
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving...' : 'Save Root Cause'}
          </button>

          {isSaved && (() => {
            const existingCapa = linkedRecords?.capa || (linkedRecords?.capas && linkedRecords.capas[0]);
            return (
              <button
                onClick={() => {
                  if (existingCapa) {
                    onNavigate?.('capa', { deviationId, capaId: existingCapa.capa_number || existingCapa.reference || existingCapa.id || 'CAPA-2026-009' });
                  } else {
                    setShowCreateCapaModal(true);
                  }
                }}
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 shadow-sm transition"
              >
                <span>{existingCapa ? 'View CAPA Workspace' : 'Create CAPA'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            );
          })()}
        </div>
      </div>

      {/* Stepper */}
      <WorkflowStepper currentStep={3} onStepClick={(step) => {
        if (step.id === 'reported') onNavigate?.('deviation_detail', { deviationId });
        if (step.id === 'investigation') onNavigate?.('investigation', { deviationId, investigationId });
        if (step.id === 'root_cause') { /* stay */ }
        if (step.id === 'capa') onNavigate?.('capa', { deviationId });
        if (step.id === 'effectiveness') onNavigate?.('effectiveness', { deviationId });
        if (step.id === 'closed') onNavigate?.('closure', { deviationId });
      }} />

      {/* Problem Statement Card */}
      <div className="bg-red-50/60 border border-red-200/80 rounded-xl p-5 shadow-xs">
        <label className="block text-xs font-bold uppercase tracking-wider text-red-900 mb-1">
          Observed Problem Statement
        </label>
        <input
          type="text"
          value={problemStatement}
          onChange={(e) => setProblemStatement(e.target.value)}
          className="w-full text-base font-semibold text-red-950 bg-white border border-red-300 rounded-lg p-3 focus:ring-2 focus:ring-red-500 shadow-inner"
        />
        <p className="text-xs text-red-700 mt-1.5">
          Formulated from In-Process Check parameter (Reactor Temp: 84 °C vs Spec 76–80 °C).
        </p>
      </div>

      {/* 5 Whys Interactive Cascade */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-indigo-600" />
            5 Whys Root Cause Exploration
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Interactively trace from the immediate physical effect down to the fundamental organizational or system breakdown.
          </p>
        </div>

        <div className="space-y-4">
          {/* Why 1 */}
          <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-blue-300 transition">
            <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center shrink-0 text-sm">
              1
            </span>
            <div className="flex-1 space-y-1">
              <label className="text-xs font-bold uppercase text-slate-500">Why 1: Immediate Effect</label>
              <input
                type="text"
                value={why1}
                onChange={(e) => setWhy1(e.target.value)}
                className="w-full text-sm font-medium text-slate-900 bg-white border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Why 2 */}
          <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-blue-300 transition ml-2 md:ml-4">
            <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center shrink-0 text-sm">
              2
            </span>
            <div className="flex-1 space-y-1">
              <label className="text-xs font-bold uppercase text-slate-500">Why 2: Physical Component</label>
              <input
                type="text"
                value={why2}
                onChange={(e) => setWhy2(e.target.value)}
                className="w-full text-sm font-medium text-slate-900 bg-white border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Why 3 */}
          <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-blue-300 transition ml-4 md:ml-8">
            <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center shrink-0 text-sm">
              3
            </span>
            <div className="flex-1 space-y-1">
              <label className="text-xs font-bold uppercase text-slate-500">Why 3: Mechanical Failure Mode</label>
              <input
                type="text"
                value={why3}
                onChange={(e) => setWhy3(e.target.value)}
                className="w-full text-sm font-medium text-slate-900 bg-white border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Why 4 */}
          <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-blue-300 transition ml-6 md:ml-12">
            <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center shrink-0 text-sm">
              4
            </span>
            <div className="flex-1 space-y-1">
              <label className="text-xs font-bold uppercase text-slate-500">Why 4: Detection & Maintenance Gap</label>
              <input
                type="text"
                value={why4}
                onChange={(e) => setWhy4(e.target.value)}
                className="w-full text-sm font-medium text-slate-900 bg-white border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Why 5 */}
          <div className="flex items-start gap-4 p-4 rounded-lg bg-indigo-50/70 border border-indigo-200 hover:border-indigo-400 transition ml-8 md:ml-16 shadow-xs">
            <span className="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center shrink-0 text-sm shadow-xs">
              5
            </span>
            <div className="flex-1 space-y-1">
              <label className="text-xs font-bold uppercase text-indigo-900">Why 5: Systemic / Quality Control Root</label>
              <input
                type="text"
                value={why5}
                onChange={(e) => setWhy5(e.target.value)}
                className="w-full text-sm font-semibold text-indigo-950 bg-white border border-indigo-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Authoritative Root Cause & Sign-off Box */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-emerald-600" />
            Authoritative Root Cause Statement
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            This root cause directly governs CAPA scope and determines required preventive SOP updates.
          </p>
        </div>

        <div>
          <textarea
            rows={3}
            value={finalRootCause}
            onChange={(e) => setFinalRootCause(e.target.value)}
            className="w-full text-base font-medium text-slate-900 bg-slate-50 border border-slate-300 rounded-lg p-3.5 focus:ring-2 focus:ring-emerald-500 leading-relaxed"
          />
        </div>

        {/* Contributing Factors */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
            Contributing Factors
          </label>
          <div className="flex flex-wrap gap-2 mb-3">
            {contributingFactors.map((factor, idx) => (
              <span key={idx} className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 border border-slate-200 text-slate-700 rounded-full text-xs font-medium">
                {factor}
                <button onClick={() => removeContributingFactor(idx)} className="hover:text-red-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2 max-w-md">
            <input
              type="text"
              placeholder="Add contributing factor..."
              value={newFactorInput}
              onChange={(e) => setNewFactorInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addContributingFactor(); } }}
              className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 flex-1"
            />
            <button
              onClick={addContributingFactor}
              className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg"
            >
              Add
            </button>
          </div>
        </div>

        {/* Human Confirmation Required Gate */}
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 flex items-start space-x-3">
          <input
            id="human-confirm"
            type="checkbox"
            checked={humanConfirmed}
            onChange={(e) => setHumanConfirmed(e.target.checked)}
            className="mt-1 w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-amber-400"
          />
          <label htmlFor="human-confirm" className="text-xs text-amber-900 leading-relaxed cursor-pointer">
            <strong>Human Quality Review & Authorization:</strong> I have evaluated the 5 Whys chain against SOP-014 v3.2 and technical maintenance records. I confirm this root cause represents the authoritative finding and will govern subsequent CAPA actions.
          </label>
        </div>
      </div>

      {/* AI 5 Whys Draft Modal */}
      {showAiModal && aiDraft && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden border border-slate-200">
            <div className="p-5 border-b border-slate-200 bg-indigo-50/50 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <div>
                  <h3 className="font-bold text-slate-900">AI Quality Assistant: 5 Whys Proposal</h3>
                  <p className="text-xs text-slate-500">Synthesized from deviation context and SOP-014 maintenance history</p>
                </div>
              </div>
              <button onClick={() => setShowAiModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-sm">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                <span>
                  <strong>Advisory Draft:</strong> You can accept this draft directly into your workspace or reject it. The final root cause requires explicit human confirmation.
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <span className="font-bold text-slate-700">Problem:</span> {aiDraft.problem_statement}
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <span className="font-bold text-slate-700">Why 1:</span> {aiDraft.why_1}
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <span className="font-bold text-slate-700">Why 2:</span> {aiDraft.why_2}
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <span className="font-bold text-slate-700">Why 3:</span> {aiDraft.why_3}
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <span className="font-bold text-slate-700">Why 4:</span> {aiDraft.why_4}
                </div>
                <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                  <span className="font-bold text-slate-700">Why 5:</span> {aiDraft.why_5}
                </div>
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-emerald-900 font-medium">
                  <span className="font-bold">Proposed Root Cause:</span> {aiDraft.final_root_cause}
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end space-x-3">
              <button
                onClick={() => setShowAiModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
              >
                Reject
              </button>
              <button
                onClick={handleAcceptAiDraft}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm"
              >
                Accept Draft into Workspace
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create CAPA Modal */}
      {showCreateCapaModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <h3 className="font-bold text-slate-900 text-lg mb-2">Initiate CAPA</h3>
            <p className="text-xs text-slate-500 mb-4">
              Directly pre-populates the confirmed root cause into corrective & preventive actions.
            </p>
            <form onSubmit={handleCreateCapaSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">CAPA Title *</label>
                <input
                  required
                  type="text"
                  value={capaTitle}
                  onChange={(e) => setCapaTitle(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">CAPA Type</label>
                  <select
                    value={capaType}
                    onChange={(e) => setCapaType(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                  >
                    <option value="Both">Corrective & Preventive</option>
                    <option value="Corrective">Corrective Only</option>
                    <option value="Preventive">Preventive Only</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Owner</label>
                  <select
                    value={capaOwner}
                    onChange={(e) => setCapaOwner(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                  >
                    <option value="Engineering">Engineering</option>
                    <option value="QA">QA</option>
                    <option value="Production">Production</option>
                    <option value="Maintenance">Maintenance</option>
                  </select>
                </div>
              </div>
              <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200">
                <strong>Governing Root Cause:</strong> {finalRootCause}
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateCapaModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingCapa}
                  className="px-5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  {isSubmittingCapa ? 'Creating...' : 'Create CAPA'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
