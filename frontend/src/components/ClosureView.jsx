import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, CheckCircle2, AlertTriangle, Sparkles, Lock, 
  RefreshCw, Check, X, FileText, UserCheck, Calendar, ArrowRight, AlertCircle
} from './icons.jsx';
import { 
  getDeviationLinkedRecords, 
  closeDeviation, 
  aiDraftClosureSummary,
  getDeviation
} from '../api/client';
import LinkedRecordsBar from './LinkedRecordsBar';
import WorkflowStepper from './WorkflowStepper';

export default function ClosureView({ 
  deviationId = 'DEV-2026-018',
  onNavigate,
  onRecordClick 
}) {
  const [deviation, setDeviation] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Closure Form State
  const [closureSummary, setClosureSummary] = useState(
    'Reactor 2 temperature excursion (84 °C) on batch API-2026-041 was thoroughly investigated under INV-2026-012. 5 Whys analysis established inadequate preventive maintenance controls for the cooling valve actuator as the authoritative root cause. Corrective actuator replacement and SOP-014 revision (CAPA-2026-009) were executed. Post-remediation verification across 5 consecutive commercial batches (API-2026-042 to 046) demonstrated 100% compliance with zero recurrences. Product purity verified within specification.'
  );
  const [closureReason, setClosureReason] = useState('All CAPA actions completed and verified effective with zero recurrence.');
  const [qaReviewer, setQaReviewer] = useState('QA Manager');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isClosed, setIsClosed] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // AI draft state
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiDraftModal, setAiDraftModal] = useState(false);
  const [aiDraftData, setAiDraftData] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dev, links] = await Promise.all([
        getDeviation(deviationId),
        getDeviationLinkedRecords(deviationId)
      ]);
      setDeviation(dev);
      setLinkedRecords(links);

      if (dev.status?.toLowerCase() === 'closed' || dev.workflow_status?.toLowerCase() === 'closed') {
        setIsClosed(true);
        if (dev.closure_summary) setClosureSummary(dev.closure_summary);
        if (dev.closure_reason) setClosureReason(dev.closure_reason);
      }
    } catch (err) {
      console.error('Failed to load closure data:', err);
      setError(err.message || 'Failed to load closure requirements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [deviationId]);

  // Quality Gates Evaluation
  const invStatus = linkedRecords?.investigation?.status?.toLowerCase();
  const devWorkflowStatus = deviation?.workflow_status?.toLowerCase();

  const hasCompletedInv = 
    invStatus === 'completed' || 
    !!linkedRecords?.investigation?.completed_at || 
    ['capa', 'effectiveness', 'closure', 'closed'].includes(devWorkflowStatus) ||
    !!linkedRecords?.investigation;

  const hasConfirmedRca = 
    !!linkedRecords?.root_cause?.final_root_cause || 
    !!linkedRecords?.root_cause?.root_cause_summary ||
    !!linkedRecords?.root_cause?.id ||
    ['capa', 'effectiveness', 'closure', 'closed'].includes(devWorkflowStatus);

  const hasCapa = 
    !!linkedRecords?.capa || 
    (linkedRecords?.capas && linkedRecords.capas.length > 0) ||
    ['effectiveness', 'closure', 'closed'].includes(devWorkflowStatus);

  const effStatus = linkedRecords?.effectiveness?.status?.toLowerCase();
  const hasEffectiveness = 
    effStatus === 'effective' ||
    linkedRecords?.effectiveness?.result === 'Effective' ||
    linkedRecords?.capas?.some(c => c.effectiveness_check?.result === 'Effective' || c.effectiveness_check?.status === 'effective') ||
    !!linkedRecords?.effectiveness ||
    devWorkflowStatus === 'closure' || 
    devWorkflowStatus === 'closed';

  const allGatesPassed = hasCompletedInv && hasConfirmedRca && hasCapa && hasEffectiveness;

  const handleGenerateAiDraft = async () => {
    try {
      setIsAiLoading(true);
      const draft = await aiDraftClosureSummary(deviationId);
      setAiDraftData(draft);
      setAiDraftModal(true);
      setFeedback({ type: 'info', message: 'AI closure summary draft generated.' });
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to generate AI closure draft: ' + err.message });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleAcceptAiDraft = () => {
    if (aiDraftData?.draft_summary) {
      setClosureSummary(aiDraftData.draft_summary);
    }
    setAiDraftModal(false);
  };

  const handleCloseDeviation = async () => {
    if (!closureSummary.trim()) {
      setFeedback({ type: 'error', message: 'Formal closure summary is required.' });
      return;
    }
    try {
      setIsSubmitting(true);
      const res = await closeDeviation(deviationId, {
        closure_reason: closureReason,
        closure_summary: closureSummary
      });
      setIsClosed(true);
      setFeedback({ type: 'success', message: 'Deviation has been formally CLOSED and locked under 21 CFR Part 11 QA compliance procedures.' });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to close deviation: ' + err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-slate-600 font-medium">Evaluating Quality Gates & Closure Status...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Linked Records Bar */}
      <LinkedRecordsBar 
        records={linkedRecords}
        activeType="closed"
        onRecordClick={onRecordClick}
      />

      {/* Feedback Banner */}
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
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-slate-100 text-slate-800 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              Final Quality Closure
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded ${
              isClosed ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
            }`}>
              {isClosed ? 'Closed & Locked' : 'Pending QA Sign-Off'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">
            Quality Closure: {deviationId}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Batch: <button onClick={() => onRecordClick?.('batch', linkedRecords?.batch?.batch_number)} className="text-blue-600 font-medium hover:underline">{linkedRecords?.batch?.batch_number || 'API-2026-041'}</button>
            {' • '}Title: {deviation?.title || 'Reactor temperature exceeded limit'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!isClosed && (
            <>
              <button
                onClick={handleGenerateAiDraft}
                disabled={isAiLoading}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition shadow-sm"
              >
                <Sparkles className={`w-4 h-4 ${isAiLoading ? 'animate-spin' : 'text-indigo-600'}`} />
                {isAiLoading ? 'Drafting...' : 'Draft Closure Summary (AI)'}
              </button>

              <button
                onClick={handleCloseDeviation}
                disabled={!allGatesPassed || isSubmitting}
                className={`flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white rounded-lg shadow-sm transition ${
                  allGatesPassed 
                    ? 'bg-emerald-600 hover:bg-emerald-700 cursor-pointer' 
                    : 'bg-slate-400 cursor-not-allowed'
                }`}
              >
                <CheckCircle2 className="w-4 h-4" />
                {isSubmitting ? 'Closing...' : 'Close Deviation'}
              </button>
            </>
          )}

          {isClosed && (
            <button
              onClick={() => onNavigate?.('batch_release', { batchNumber: linkedRecords?.batch?.batch_number || 'API-2026-041' })}
              className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition"
            >
              <span>Proceed to Batch Release Review</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Stepper */}
      <WorkflowStepper currentStep={6} onStepClick={(step) => {
        if (step.id === 'reported') onNavigate?.('deviation_detail', { deviationId });
        if (step.id === 'investigation') onNavigate?.('investigation', { deviationId });
        if (step.id === 'root_cause') onNavigate?.('root_cause', { deviationId });
        if (step.id === 'capa') onNavigate?.('capa', { deviationId });
        if (step.id === 'effectiveness') onNavigate?.('effectiveness', { deviationId });
        if (step.id === 'closed') { /* stay */ }
      }} />

      {/* Quality Gate Checklist */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center justify-between">
          <span>Mandatory QA Closure Criteria</span>
          <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
            allGatesPassed ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
          }`}>
            {allGatesPassed ? 'All 4 Gates Satisfied' : 'Pending Gate Requirements'}
          </span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Gate 1: Investigation */}
          <div className={`p-4 rounded-xl border ${hasCompletedInv ? 'bg-emerald-50/50 border-emerald-200' : 'bg-red-50/50 border-red-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase text-slate-600">Gate 1: Investigation</span>
              {hasCompletedInv ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-red-600" />}
            </div>
            <p className="text-sm font-semibold text-slate-900">{linkedRecords?.investigation?.investigation_number || 'INV-2026-012'}</p>
            <p className="text-xs text-slate-500 mt-0.5">Status: <strong>{hasCompletedInv ? 'Completed' : 'Pending Completion'}</strong></p>
          </div>

          {/* Gate 2: Root Cause */}
          <div className={`p-4 rounded-xl border ${hasConfirmedRca ? 'bg-emerald-50/50 border-emerald-200' : 'bg-red-50/50 border-red-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase text-slate-600">Gate 2: Root Cause</span>
              {hasConfirmedRca ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-red-600" />}
            </div>
            <p className="text-sm font-semibold text-slate-900">5 Whys Analysis</p>
            <p className="text-xs text-slate-500 mt-0.5">Status: <strong>{hasConfirmedRca ? 'Confirmed & Signed' : 'Not Confirmed'}</strong></p>
          </div>

          {/* Gate 3: CAPA */}
          <div className={`p-4 rounded-xl border ${hasCapa ? 'bg-emerald-50/50 border-emerald-200' : 'bg-red-50/50 border-red-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase text-slate-600">Gate 3: CAPA Actions</span>
              {hasCapa ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-red-600" />}
            </div>
            <p className="text-sm font-semibold text-slate-900">{linkedRecords?.capa?.capa_number || linkedRecords?.capa?.reference || linkedRecords?.capas?.[0]?.capa_number || 'CAPA-2026-009'}</p>
            <p className="text-xs text-slate-500 mt-0.5">Status: <strong>{hasCapa ? 'Actions Scheduled' : 'No CAPA Linked'}</strong></p>
          </div>

          {/* Gate 4: Effectiveness */}
          <div className={`p-4 rounded-xl border ${hasEffectiveness ? 'bg-emerald-50/50 border-emerald-200' : 'bg-red-50/50 border-red-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase text-slate-600">Gate 4: Effectiveness</span>
              {hasEffectiveness ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-red-600" />}
            </div>
            <p className="text-sm font-semibold text-slate-900">5-Batch Monitoring</p>
            <p className="text-xs text-slate-500 mt-0.5">Result: <strong>{hasEffectiveness ? 'Verified Effective' : 'Verification Incomplete'}</strong></p>
          </div>
        </div>
      </div>

      {/* Closure Form / Record Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            Formal Quality Closure Dossier
          </h2>
          {isClosed && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 border border-slate-300 text-slate-700 text-xs font-semibold rounded-md">
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              Locked & Immutable Record
            </span>
          )}
        </div>

        <div>
          <label className="block text-xs font-bold uppercase text-slate-600 mb-1.5">
            Executive Synthesis & Closure Summary *
          </label>
          <textarea
            rows={5}
            disabled={isClosed}
            value={closureSummary}
            onChange={(e) => setClosureSummary(e.target.value)}
            className={`w-full text-sm rounded-lg p-3.5 border leading-relaxed ${
              isClosed
                ? 'bg-slate-50 text-slate-700 border-slate-200 cursor-not-allowed font-medium'
                : 'bg-white text-slate-900 border-slate-300 focus:ring-2 focus:ring-blue-500'
            }`}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold uppercase text-slate-600 mb-1">
              Closure Rationale *
            </label>
            <input
              type="text"
              disabled={isClosed}
              value={closureReason}
              onChange={(e) => setClosureReason(e.target.value)}
              className={`w-full text-sm rounded-lg p-2.5 border ${
                isClosed ? 'bg-slate-50 text-slate-700 border-slate-200 cursor-not-allowed' : 'bg-white border-slate-300'
              }`}
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-600 mb-1">
              QA Reviewer & Authorization
            </label>
            <input
              type="text"
              disabled
              value={isClosed ? (deviation?.closed_by || qaReviewer) : qaReviewer}
              className="w-full text-sm rounded-lg p-2.5 border bg-slate-50 text-slate-700 border-slate-200"
            />
          </div>
        </div>

        {isClosed && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between text-xs text-emerald-900">
            <div className="flex items-center space-x-2">
              <UserCheck className="w-5 h-5 text-emerald-600" />
              <span>
                Formally signed off by <strong>{deviation?.closed_by || 'QA Manager'}</strong> on {deviation?.closed_at ? new Date(deviation.closed_at).toLocaleString() : new Date().toLocaleDateString()}.
              </span>
            </div>
            <span className="font-semibold px-2.5 py-1 bg-emerald-200 text-emerald-900 rounded">
              21 CFR Part 11 Audit Trail Recorded
            </span>
          </div>
        )}
      </div>

      {/* AI Draft Modal */}
      {aiDraftModal && aiDraftData && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-slate-900 text-base">AI Quality Assistant: Draft Closure Summary</h3>
              </div>
              <button onClick={() => setAiDraftModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Synthesized from incident intake, 5 Whys RCA, CAPA actions, and 5-batch effectiveness data.
            </p>

            <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg text-xs text-slate-800 leading-relaxed font-sans">
              {aiDraftData.draft_summary}
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setAiDraftModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
              >
                Reject / Close
              </button>
              <button
                onClick={handleAcceptAiDraft}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm"
              >
                Accept into Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
