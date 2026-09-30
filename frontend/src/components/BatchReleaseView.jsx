import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, CheckCircle2, AlertTriangle, XCircle, Clock, 
  RefreshCw, Check, X, FileText, UserCheck, Layers, ArrowLeft
} from './icons.jsx';
import { 
  getBatchRelease, 
  decideBatchRelease,
  getBatch
} from '../api/client';
import LinkedRecordsBar from './LinkedRecordsBar';

export default function BatchReleaseView({ 
  batchReleaseId = 'BR-2026-041', 
  batchNumber = 'API-2026-041',
  onNavigate,
  onRecordClick 
}) {
  const [releaseRecord, setReleaseRecord] = useState(null);
  const [batchData, setBatchData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Disposition Form State
  const [disposition, setDisposition] = useState('Pending');
  const [rationale, setRationale] = useState(
    'All critical in-process checks and deviations (DEV-2026-018) have been fully investigated and formally closed. Post-remediation CAPA verified effective. Finished product HPLC assay (99.8%) and impurity profiling comply with Paracetamol API release specifications.'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [feedback, setFeedback] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getBatchRelease(batchReleaseId);
      setReleaseRecord(data);
      const initialDisp = data.disposition || (data.status ? (data.status.toLowerCase() === 'released' ? 'Released' : data.status.toLowerCase() === 'pending' ? 'Pending' : data.status) : 'Pending');
      setDisposition(initialDisp);
      if (data.rationale) setRationale(data.rationale);

      if (data.batch_id || batchNumber) {
        try {
          const b = await getBatch(data.batch_id || batchNumber);
          setBatchData(b);
        } catch (e) {
          console.warn('Could not fetch batch details', e);
        }
      }
    } catch (err) {
      console.error('Failed to load batch release record:', err);
      setError(err.message || 'Failed to load batch release record.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [batchReleaseId]);

  const handleDecisionSubmit = async (selectedDisposition) => {
    if (!rationale.trim()) {
      setFeedback({ type: 'error', message: 'Formal QA rationale is mandatory before recording disposition.' });
      return;
    }
    try {
      setIsSubmitting(true);
      await decideBatchRelease(releaseRecord.id, {
        decision: selectedDisposition.toUpperCase(),
        disposition: selectedDisposition,
        rationale: rationale,
        comments: rationale
      });
      setDisposition(selectedDisposition);
      setFeedback({ type: 'success', message: `Batch disposition successfully recorded as ${selectedDisposition}.` });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to record disposition: ' + err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-slate-600 font-medium">Loading Batch Release Dossier...</div>
      </div>
    );
  }

  const checklistItems = [
    { title: 'In-process checks reviewed', status: 'PASS (with deviation)', detail: 'Temperature 84 °C handled via DEV-2026-018', passed: true },
    { title: 'Deviations closed', status: 'DEV-2026-018 CLOSED', detail: 'Formal QA sign-off recorded', passed: true },
    { title: 'Investigation completed', status: 'INV-2026-012 COMPLETED', detail: 'Root cause and product impact assessed', passed: true },
    { title: 'CAPA initiated & verified', status: 'CAPA-2026-009 EFFECTIVE', detail: '5/5 monitoring batches compliant', passed: true },
    { title: 'Analytical release testing', status: 'MEETS SPEC', detail: 'Purity 99.8%, Water content 0.12%', passed: true }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-4 rounded-xl border text-xs flex items-center justify-between shadow-xs transition-all ${
          feedback.type === 'error'
            ? 'bg-red-50 text-red-800 border-red-200'
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
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-slate-100 text-slate-800">
              QA Disposition & Release
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded ${
              disposition === 'Released'
                ? 'bg-emerald-100 text-emerald-800'
                : disposition === 'Rejected'
                ? 'bg-red-100 text-red-800'
                : disposition === 'Quarantined'
                ? 'bg-amber-100 text-amber-800'
                : 'bg-blue-100 text-blue-800'
            }`}>
              {disposition === 'Released' ? 'Batch Released' : disposition === 'Pending' ? 'Pending QA Disposition' : disposition}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">
            Release Dossier: Batch {batchData?.batch_number || batchNumber}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Product: <strong className="text-slate-700">{batchData?.product_name || 'Paracetamol API'}</strong>
            {' • '}Recipe: <span className="font-mono text-slate-700">{batchData?.recipe_version || 'v4.2'}</span>
            {' • '}Site: <span className="text-slate-700">{batchData?.site || 'Bengaluru'}</span>
          </p>
        </div>

        <button
          onClick={() => onNavigate?.('batches', { batchNumber: batchData?.batch_number || batchNumber })}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Batch
        </button>
      </div>

      {/* Release Checklist */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            Quality Assurance Release Checklist
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Connected quality lifecycle verification required prior to commercial release authorization.
          </p>
        </div>

        <div className="space-y-3">
          {checklistItems.map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-slate-900">{item.title}</h4>
                  <p className="text-xs text-slate-500">{item.detail}</p>
                </div>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Disposition Decision Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          QA Release Disposition & Rationale
        </h2>

        <div>
          <label className="block text-xs font-bold uppercase text-slate-600 mb-1.5">
            QA Release Rationale *
          </label>
          <textarea
            rows={4}
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            className="w-full text-sm rounded-lg p-3 border border-slate-300 focus:ring-2 focus:ring-blue-500 leading-relaxed"
          />
        </div>

        <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-slate-500 flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-slate-400" />
            <span>Authorized by: <strong>{releaseRecord?.released_by || 'QA Qualified Person (QP)'}</strong></span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleDecisionSubmit('Rejected')}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-red-700 bg-red-50 border border-red-300 rounded-lg hover:bg-red-100 transition"
            >
              <XCircle className="w-4 h-4" />
              Reject Batch
            </button>

            <button
              onClick={() => handleDecisionSubmit('Quarantined')}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-amber-700 bg-amber-50 border border-amber-300 rounded-lg hover:bg-amber-100 transition"
            >
              <Clock className="w-4 h-4" />
              Quarantine
            </button>

            <button
              onClick={() => handleDecisionSubmit('Released')}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 shadow-sm transition"
            >
              <Check className="w-4 h-4 stroke-[3]" />
              Authorize Release
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
