import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, AlertTriangle, ShieldCheck, Sparkles, ArrowRight, 
  RefreshCw, Check, X, Layers, FileCheck, ThumbsUp, ThumbsDown
} from './icons.jsx';
import { 
  getCapa, 
  recordCapaEffectiveness, 
  aiSummarizeEffectiveness,
  getDeviationLinkedRecords 
} from '../api/client';
import LinkedRecordsBar from './LinkedRecordsBar';
import WorkflowStepper from './WorkflowStepper';

export default function EffectivenessView({ 
  capaId = 'CAPA-2026-009', 
  deviationId = 'DEV-2026-018',
  onNavigate,
  onRecordClick 
}) {
  const [capa, setCapa] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 5 Monitored batches state
  const [monitoredBatches, setMonitoredBatches] = useState([
    { batchNumber: 'API-2026-042', product: 'Paracetamol API', reactor: 'Reactor 2', status: 'In Spec', maxTemp: '78.8 °C', result: 'Pass' },
    { batchNumber: 'API-2026-043', product: 'Paracetamol API', reactor: 'Reactor 2', status: 'In Spec', maxTemp: '79.1 °C', result: 'Pass' },
    { batchNumber: 'API-2026-044', product: 'Paracetamol API', reactor: 'Reactor 2', status: 'In Spec', maxTemp: '78.4 °C', result: 'Pass' },
    { batchNumber: 'API-2026-045', product: 'Paracetamol API', reactor: 'Reactor 2', status: 'In Spec', maxTemp: '79.5 °C', result: 'Pass' },
    { batchNumber: 'API-2026-046', product: 'Paracetamol API', reactor: 'Reactor 2', status: 'In Spec', maxTemp: '78.9 °C', result: 'Pass' }
  ]);

  const [decision, setDecision] = useState('Effective'); // 'Effective' | 'Ineffective' | 'Pending'
  const [summaryText, setSummaryText] = useState(
    '5/5 consecutive commercial batches produced on Reactor 2 following actuator replacement and revised PM checklist demonstrated compliant thermal profiles within 76–80 °C with zero recurrent excursions.'
  );
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCapa(capaId);
      setCapa(data);

      if (data.effectiveness_check) {
        const eff = data.effectiveness_check;
        const rawDecision = eff.result || eff.status || '';
        if (rawDecision) {
          setDecision(rawDecision.toLowerCase() === 'effective' ? 'Effective' : rawDecision.toLowerCase() === 'ineffective' ? 'Ineffective' : 'Pending');
        }
        if (eff.summary || eff.comments) setSummaryText(eff.summary || eff.comments);
        if (eff.verified_batches && Array.isArray(eff.verified_batches) && eff.verified_batches.length > 0) {
          setMonitoredBatches(eff.verified_batches);
        }
        setSavedSuccess(true);
      }

      const devTarget = data.deviation_id || deviationId;
      if (devTarget) {
        try {
          const links = await getDeviationLinkedRecords(devTarget);
          setLinkedRecords(links);
        } catch (e) {
          console.warn('Could not fetch linked records', e);
        }
      }
    } catch (err) {
      console.error('Failed to load effectiveness data:', err);
      setError(err.message || 'Failed to load effectiveness check.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [capaId]);

  const handleGenerateAiSummary = async () => {
    try {
      setIsAiLoading(true);
      const res = await aiSummarizeEffectiveness(capa.id, monitoredBatches);
      if (res.summary) {
        setSummaryText(res.summary);
      }
      if (res.recommended_result) {
        setDecision(res.recommended_result);
      }
      setFeedback({ type: 'info', message: 'AI effectiveness summary draft generated based on 5 monitored batches.' });
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to generate AI summary: ' + err.message });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleSaveDecision = async (selectedResult) => {
    try {
      setIsSubmitting(true);
      const statusLower = selectedResult.toLowerCase();
      await recordCapaEffectiveness(capa.id, {
        plan: 'Monitor the next five batches of Paracetamol API on Reactor 2 for temperature excursion recurrence.',
        verified_batches: monitoredBatches,
        result: selectedResult,
        status: statusLower,
        summary: summaryText,
        comments: summaryText,
        reviewed_by: 'QA Manager'
      });
      setDecision(selectedResult);
      setSavedSuccess(true);
      setFeedback({ type: 'success', message: `Effectiveness verification recorded as ${selectedResult}. Quality Closure gate satisfied.` });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to record effectiveness decision: ' + err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-slate-600 font-medium">Loading Effectiveness Verification...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Linked Records Bar */}
      <LinkedRecordsBar 
        records={linkedRecords}
        activeType="effectiveness"
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
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-emerald-100 text-emerald-800 flex items-center gap-1.5">
              <FileCheck className="w-3.5 h-3.5" />
              Effectiveness Verification
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded ${
              decision === 'Effective' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {decision}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">
            Verification Protocol: 5-Batch Recurrence Monitoring
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Governing CAPA: <button onClick={() => onRecordClick?.('capa', capaId)} className="text-blue-600 font-medium hover:underline">{capaId}</button>
            {' • '}Deviation: <button onClick={() => onRecordClick?.('deviation', deviationId)} className="text-blue-600 font-medium hover:underline">{deviationId}</button>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerateAiSummary}
            disabled={isAiLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition shadow-sm"
          >
            <Sparkles className={`w-4 h-4 ${isAiLoading ? 'animate-spin' : 'text-indigo-600'}`} />
            {isAiLoading ? 'Analyzing...' : 'Generate Effectiveness Summary'}
          </button>

          {savedSuccess && (
            <button
              onClick={() => onNavigate?.('closure', { deviationId })}
              className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition"
            >
              <span>Proceed to Quality Closure</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Stepper */}
      <WorkflowStepper currentStep={5} onStepClick={(step) => {
        if (step.id === 'reported') onNavigate?.('deviation_detail', { deviationId });
        if (step.id === 'investigation') onNavigate?.('investigation', { deviationId });
        if (step.id === 'root_cause') onNavigate?.('root_cause', { deviationId });
        if (step.id === 'capa') onNavigate?.('capa', { deviationId });
        if (step.id === 'effectiveness') { /* stay */ }
        if (step.id === 'closed') onNavigate?.('closure', { deviationId });
      }} />

      {/* Protocol Banner */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-2">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">Verification Plan</h3>
        <p className="text-sm text-slate-800 leading-relaxed">
          Monitor the next five consecutive batches of <strong>Paracetamol API</strong> on <strong>Reactor 2</strong> for temperature excursion recurrence. All batches must strictly conform to the 76–80 °C operating boundary.
        </p>
      </div>

      {/* 5-Batch Verification Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div>
            <h2 className="text-base font-bold text-slate-900">Monitored Production Batches</h2>
            <p className="text-xs text-slate-500 mt-0.5">Verification criteria: 5 consecutive batches with zero out-of-spec excursions</p>
          </div>
          <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" />
            Result: 5/5 Batches Compliant (100%)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100/70 text-xs uppercase tracking-wider text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 font-semibold">Batch ID</th>
                <th className="px-6 py-3 font-semibold">Product</th>
                <th className="px-6 py-3 font-semibold">Equipment</th>
                <th className="px-6 py-3 font-semibold">Peak Temperature</th>
                <th className="px-6 py-3 font-semibold">Thermal Status</th>
                <th className="px-6 py-3 font-semibold">Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {monitoredBatches.map((b, idx) => (
                <tr key={idx} className="hover:bg-slate-50 transition">
                  <td className="px-6 py-3.5 font-bold text-slate-900">{b.batchNumber}</td>
                  <td className="px-6 py-3.5 text-slate-700">{b.product}</td>
                  <td className="px-6 py-3.5 text-slate-600">{b.reactor}</td>
                  <td className="px-6 py-3.5 font-mono text-slate-900">{b.maxTemp}</td>
                  <td className="px-6 py-3.5">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {b.status}
                    </span>
                  </td>
                  <td className="px-6 py-3.5">
                    <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
                      <Check className="w-4 h-4 stroke-[3]" /> Pass
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rationale & Decision Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <h2 className="text-base font-bold text-slate-900">Effectiveness Assessment & Rationale</h2>
        
        <div>
          <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
            Quality Evidence Summary
          </label>
          <textarea
            rows={3}
            value={summaryText}
            onChange={(e) => setSummaryText(e.target.value)}
            className="w-full text-sm text-slate-800 bg-slate-50 border border-slate-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 leading-relaxed"
          />
        </div>

        <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500">
            Human Quality authorization required. Selecting a decision records an immutable audit trail entry.
          </p>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleSaveDecision('Ineffective')}
              disabled={isSubmitting}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg border transition ${
                decision === 'Ineffective'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-white text-red-600 border-red-300 hover:bg-red-50'
              }`}
            >
              <ThumbsDown className="w-4 h-4" />
              Mark Ineffective
            </button>

            <button
              onClick={() => handleSaveDecision('Effective')}
              disabled={isSubmitting}
              className={`flex items-center gap-2 px-5 py-2 text-xs font-bold rounded-lg shadow-sm transition ${
                decision === 'Effective'
                  ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                  : 'bg-white text-emerald-700 border border-emerald-400 hover:bg-emerald-50'
              }`}
            >
              <ThumbsUp className="w-4 h-4" />
              Mark Effective
            </button>
          </div>
        </div>

        {/* Quality Loop Outcome Navigation */}
        {decision === 'Ineffective' && (
          <div className="rounded-xl border border-red-200 bg-red-50/90 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔄</span>
              <div>
                <h4 className="text-xs font-bold text-red-900 uppercase tracking-wider">Quality Loop Triggered (Issue Recurred)</h4>
                <p className="text-xs text-red-700 mt-0.5">
                  Effectiveness verification failed. Workflow status reset to Investigation for re-evaluation and root cause reassessment.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onNavigate?.('investigation', { deviationId, investigationId: 'INV-2026-012' })}
              className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700 transition shrink-0"
            >
              <span>Return to Investigation →</span>
            </button>
          </div>
        )}

        {decision === 'Effective' && savedSuccess && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/90 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-center gap-3">
              <span className="text-2xl">✓</span>
              <div>
                <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider">Quality Loop Satisfied (Zero Recurrence)</h4>
                <p className="text-xs text-emerald-700 mt-0.5">
                  5/5 batches verified effective. All corrective and preventive actions confirmed. Ready for formal Deviation Closure.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onNavigate?.('closure', { deviationId })}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 transition shrink-0"
            >
              <span>Proceed to Deviation Closure →</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
