import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, CheckCircle2, Clock, AlertTriangle, Sparkles, 
  ArrowRight, Plus, ExternalLink, RefreshCw, Check, X, 
  Calendar, User, Tool, Layers, ChevronRight, FileText
} from './icons.jsx';
import { 
  getCapa, 
  addCapaAction, 
  updateCapaAction, 
  aiSuggestCapaActions,
  getDeviationLinkedRecords
} from '../api/client';
import LinkedRecordsBar from './LinkedRecordsBar';
import WorkflowStepper from './WorkflowStepper';

export default function CapaWorkspaceView({ 
  capaId = 'CAPA-2026-009', 
  deviationId = 'DEV-2026-018',
  onNavigate,
  onRecordClick 
}) {
  const [capa, setCapa] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // AI Suggestion State
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState(null);
  const [showAiModal, setShowAiModal] = useState(false);

  // Add Action Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [actionCategory, setActionCategory] = useState('Corrective');
  const [actionDesc, setActionDesc] = useState('');
  const [actionOwner, setActionOwner] = useState('Engineering');
  const [actionDueDate, setActionDueDate] = useState('');
  const [actionVerificationPlan, setActionVerificationPlan] = useState('');
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCapa(capaId);
      setCapa(data);

      const devTarget = data.deviation_id || deviationId;
      if (devTarget) {
        try {
          const links = await getDeviationLinkedRecords(devTarget);
          setLinkedRecords(links);
        } catch (e) {
          console.warn('Could not load linked records', e);
        }
      }
    } catch (err) {
      console.error('Failed to load CAPA:', err);
      setError(err.message || 'Failed to load CAPA details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [capaId]);

  const handleToggleActionStatus = async (action) => {
    try {
      const nextStatus = action.status === 'Completed' ? 'In Progress' : 'Completed';
      await updateCapaAction(capa.id, action.id, { 
        status: nextStatus,
        completed_at: nextStatus === 'Completed' ? new Date().toISOString() : null
      });
      setFeedback({ type: 'success', message: `Action updated to "${nextStatus}".` });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to update action status: ' + err.message });
    }
  };

  const handleAddActionSubmit = async (e) => {
    e.preventDefault();
    if (!actionDesc.trim()) return;
    try {
      setIsSubmittingAction(true);
      await addCapaAction(capa.id, {
        action_type: actionCategory,
        description: actionDesc,
        action_description: actionDesc,
        owner: actionOwner,
        due_date: actionDueDate || '2026-10-15',
        verification_plan: actionVerificationPlan || undefined,
        evidence_reference: actionVerificationPlan || undefined,
        status: 'Open'
      });
      setShowAddModal(false);
      setActionDesc('');
      setActionVerificationPlan('');
      setFeedback({ type: 'success', message: 'New CAPA action added successfully.' });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to add action: ' + err.message });
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleRunAiSuggestions = async () => {
    try {
      setIsAiLoading(true);
      const res = await aiSuggestCapaActions(
        capa.id, 
        capa.root_cause_summary || 'Inadequate preventive-maintenance control for cooling-valve actuator', 
        capa.deviation_id || deviationId
      );
      setAiSuggestions(res);
      setShowAiModal(true);
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to get AI CAPA suggestions: ' + err.message });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleAcceptAiActions = async () => {
    if (!aiSuggestions) return;
    // Add corrective actions
    const corrs = aiSuggestions.corrective_actions || aiSuggestions.suggested_corrective || [];
    if (corrs.length) {
      for (const act of corrs) {
        try {
          const desc = act.description || act.action_description || (typeof act === 'string' ? act : 'Corrective Action');
          const verPlan = act.verification_evidence || act.verification_plan || act.evidence_reference || 'Maintenance inspection log';
          await addCapaAction(capa.id, {
            action_type: 'Corrective',
            description: desc,
            action_description: desc,
            owner: act.owner || 'Engineering',
            due_date: act.due_date || '2026-10-15',
            verification_plan: verPlan,
            evidence_reference: verPlan,
            status: 'Open'
          });
        } catch (e) {
          console.warn('Failed to add suggested corrective action', e);
        }
      }
    }
    // Add preventive actions
    const prevs = aiSuggestions.preventive_actions || aiSuggestions.suggested_preventive || [];
    if (prevs.length) {
      for (const act of prevs) {
        try {
          const desc = act.description || act.action_description || (typeof act === 'string' ? act : 'Preventive Action');
          const verPlan = act.verification_evidence || act.verification_plan || act.evidence_reference || 'Revised SOP document';
          await addCapaAction(capa.id, {
            action_type: 'Preventive',
            description: desc,
            action_description: desc,
            owner: act.owner || 'Maintenance',
            due_date: act.due_date || '2026-10-15',
            verification_plan: verPlan,
            evidence_reference: verPlan,
            status: 'Open'
          });
        } catch (e) {
          console.warn('Failed to add suggested preventive action', e);
        }
      }
    }
    setShowAiModal(false);
    setFeedback({ type: 'success', message: 'AI CAPA suggestions successfully applied to the plan.' });
    fetchDetails();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-slate-600 font-medium">Loading CAPA Workspace...</div>
      </div>
    );
  }

  if (error || !capa) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl flex items-center space-x-3">
          <AlertTriangle className="w-6 h-6 shrink-0" />
          <div>
            <h3 className="font-semibold text-lg">CAPA Record Not Found</h3>
            <p className="text-sm mt-1">{error || 'Unable to retrieve CAPA record.'}</p>
          </div>
        </div>
      </div>
    );
  }

  const correctiveActions = capa.actions?.filter(a => a.action_type === 'Corrective') || [];
  const preventiveActions = capa.actions?.filter(a => a.action_type === 'Preventive') || [];
  const allActionsCompleted = capa.actions?.length > 0 && capa.actions.every(a => a.status === 'Completed');

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Linked Records Bar */}
      <LinkedRecordsBar 
        records={linkedRecords}
        activeType="capa"
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
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-blue-100 text-blue-800">
              CAPA Workspace
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 rounded bg-amber-100 text-amber-800">
              {capa.status}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">
            {capa.capa_number}: {capa.title}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Linked Deviation: <button onClick={() => onRecordClick?.('deviation', deviationId)} className="text-blue-600 font-medium hover:underline">{deviationId}</button>
            {' • '}Assigned Owner: <span className="font-medium text-slate-700">{capa.assigned_owner || 'Engineering'}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAiSuggestions}
            disabled={isAiLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition shadow-sm"
          >
            <Sparkles className={`w-4 h-4 ${isAiLoading ? 'animate-spin' : 'text-indigo-600'}`} />
            {isAiLoading ? 'Analyzing RCA...' : 'Suggest CAPA Actions'}
          </button>

          <button
            onClick={() => {
              setActionCategory('Corrective');
              setShowAddModal(true);
            }}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 transition"
          >
            <Plus className="w-4 h-4" />
            Add Action
          </button>

          <button
            onClick={() => onNavigate?.('effectiveness', { deviationId, capaId: capa.capa_number })}
            className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition"
          >
            <span>Proceed to Effectiveness Check</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stepper */}
      <WorkflowStepper currentStep={4} onStepClick={(step) => {
        if (step.id === 'reported') onNavigate?.('deviation_detail', { deviationId });
        if (step.id === 'investigation') onNavigate?.('investigation', { deviationId });
        if (step.id === 'root_cause') onNavigate?.('root_cause', { deviationId });
        if (step.id === 'capa') { /* stay */ }
        if (step.id === 'effectiveness') onNavigate?.('effectiveness', { deviationId, capaId: capa.capa_number });
        if (step.id === 'closed') onNavigate?.('closure', { deviationId });
      }} />

      {/* Governing Root Cause Banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3">
        <ShieldCheck className="w-5 h-5 text-emerald-600 mt-0.5 shrink-0" />
        <div className="text-xs text-slate-700 leading-relaxed">
          <strong className="text-slate-900 block font-semibold text-sm mb-0.5">Authoritative Governing Root Cause</strong>
          {capa.root_cause_summary || 'Inadequate preventive-maintenance control for the cooling-valve actuator.'}
        </div>
      </div>

      {/* Actions Split Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Corrective Actions Section */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                Corrective Actions
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Immediate repair and physical restoration</p>
            </div>
            <button
              onClick={() => {
                setActionCategory('Corrective');
                setShowAddModal(true);
              }}
              className="text-xs text-blue-600 font-semibold hover:text-blue-800 flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> New
            </button>
          </div>

          <div className="space-y-3">
            {correctiveActions.map((act) => (
              <div 
                key={act.id} 
                className={`p-4 rounded-lg border transition ${
                  act.status === 'Completed' ? 'bg-slate-50/70 border-slate-200' : 'bg-white border-blue-200 shadow-xs'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start space-x-3">
                    <button
                      onClick={() => handleToggleActionStatus(act)}
                      className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center border transition ${
                        act.status === 'Completed'
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-slate-300 hover:border-blue-500 text-transparent'
                      }`}
                      title="Toggle completion"
                    >
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </button>
                    <div>
                      <h4 className={`text-sm font-semibold ${
                        act.status === 'Completed' ? 'line-through text-slate-400' : 'text-slate-800'
                      }`}>
                        {act.description || act.action_description}
                      </h4>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-2">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3 text-slate-400" />
                          Owner: <strong>{act.owner}</strong>
                        </span>
                        {act.due_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            Due: {act.due_date}
                          </span>
                        )}
                      </div>
                      {(act.verification_plan || act.evidence_reference) && (
                        <p className="text-[11px] text-slate-500 mt-2 bg-slate-50 p-2 rounded border border-slate-200">
                          <strong>Verification:</strong> {act.verification_plan || act.evidence_reference}
                        </p>
                      )}
                    </div>
                  </div>

                  <span className={`text-[11px] px-2 py-0.5 rounded font-semibold shrink-0 ${
                    act.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-50 text-blue-700'
                  }`}>
                    {act.status}
                  </span>
                </div>
              </div>
            ))}

            {correctiveActions.length === 0 && (
              <div className="text-center py-6 text-xs text-slate-400 italic bg-slate-50 rounded-lg">
                No corrective actions logged.
              </div>
            )}
          </div>
        </div>

        {/* Preventive Actions Section */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span>
                Preventive Actions
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Procedural updates, calibration, and recurrence prevention</p>
            </div>
            <button
              onClick={() => {
                setActionCategory('Preventive');
                setShowAddModal(true);
              }}
              className="text-xs text-blue-600 font-semibold hover:text-blue-800 flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> New
            </button>
          </div>

          <div className="space-y-3">
            {preventiveActions.map((act) => (
              <div 
                key={act.id} 
                className={`p-4 rounded-lg border transition ${
                  act.status === 'Completed' ? 'bg-slate-50/70 border-slate-200' : 'bg-white border-emerald-200 shadow-xs'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start space-x-3">
                    <button
                      onClick={() => handleToggleActionStatus(act)}
                      className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center border transition ${
                        act.status === 'Completed'
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-slate-300 hover:border-emerald-500 text-transparent'
                      }`}
                      title="Toggle completion"
                    >
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </button>
                    <div>
                      <h4 className={`text-sm font-semibold ${
                        act.status === 'Completed' ? 'line-through text-slate-400' : 'text-slate-800'
                      }`}>
                        {act.description || act.action_description}
                      </h4>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-2">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3 text-slate-400" />
                          Owner: <strong>{act.owner}</strong>
                        </span>
                        {act.due_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            Due: {act.due_date}
                          </span>
                        )}
                      </div>
                      {(act.verification_plan || act.evidence_reference) && (
                        <p className="text-[11px] text-slate-500 mt-2 bg-slate-50 p-2 rounded border border-slate-200">
                          <strong>Verification:</strong> {act.verification_plan || act.evidence_reference}
                        </p>
                      )}
                    </div>
                  </div>

                  <span className={`text-[11px] px-2 py-0.5 rounded font-semibold shrink-0 ${
                    act.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {act.status}
                  </span>
                </div>
              </div>
            ))}

            {preventiveActions.length === 0 && (
              <div className="text-center py-6 text-xs text-slate-400 italic bg-slate-50 rounded-lg">
                No preventive actions logged.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Suggestions Modal */}
      {showAiModal && aiSuggestions && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden border border-slate-200">
            <div className="p-5 border-b border-slate-200 bg-indigo-50/50 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <div>
                  <h3 className="font-bold text-slate-900">AI Quality Assistant: CAPA Proposals</h3>
                  <p className="text-xs text-slate-500">Based on root cause analysis and equipment reliability standards</p>
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
                  <strong>Advisory:</strong> These proposed actions will be populated into the CAPA workspace where each item can be independently scheduled and tracked.
                </span>
              </div>

              <div>
                <h4 className="font-semibold text-slate-800 mb-2">Suggested Corrective Actions</h4>
                <div className="space-y-2">
                  {aiSuggestions.corrective_actions?.map((ca, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded border border-slate-200 text-xs">
                      <p className="font-semibold text-slate-800">{ca.description || ca}</p>
                      <div className="text-slate-500 mt-1 flex gap-3 text-[11px]">
                        <span>Owner: {ca.owner || 'Engineering'}</span>
                        <span>Evidence: {ca.verification_evidence || 'Work order sign-off'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-slate-800 mb-2">Suggested Preventive Actions</h4>
                <div className="space-y-2">
                  {aiSuggestions.preventive_actions?.map((pa, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded border border-slate-200 text-xs">
                      <p className="font-semibold text-slate-800">{pa.description || pa}</p>
                      <div className="text-slate-500 mt-1 flex gap-3 text-[11px]">
                        <span>Owner: {pa.owner || 'Maintenance'}</span>
                        <span>Evidence: {pa.verification_evidence || 'SOP revision record'}</span>
                      </div>
                    </div>
                  ))}
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
                onClick={handleAcceptAiActions}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm"
              >
                Accept and Populate Actions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Action Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <h3 className="font-bold text-slate-900 text-lg mb-2">Add CAPA Action</h3>
            <form onSubmit={handleAddActionSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Category</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setActionCategory('Corrective')}
                    className={`py-2 text-xs font-semibold rounded-lg border text-center ${
                      actionCategory === 'Corrective'
                        ? 'bg-blue-50 border-blue-600 text-blue-700'
                        : 'border-slate-300 text-slate-600'
                    }`}
                  >
                    Corrective
                  </button>
                  <button
                    type="button"
                    onClick={() => setActionCategory('Preventive')}
                    className={`py-2 text-xs font-semibold rounded-lg border text-center ${
                      actionCategory === 'Preventive'
                        ? 'bg-emerald-50 border-emerald-600 text-emerald-700'
                        : 'border-slate-300 text-slate-600'
                    }`}
                  >
                    Preventive
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Description *</label>
                <textarea
                  required
                  rows={3}
                  value={actionDesc}
                  onChange={(e) => setActionDesc(e.target.value)}
                  placeholder={actionCategory === 'Corrective' 
                    ? 'e.g. Replace the malfunctioning cooling-valve actuator on Reactor 2' 
                    : 'e.g. Update SOP-014 PM checklist to inspect actuator response every 30 days'}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Owner</label>
                  <select
                    value={actionOwner}
                    onChange={(e) => setActionOwner(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                  >
                    <option value="Engineering">Engineering</option>
                    <option value="Maintenance">Maintenance</option>
                    <option value="QA">QA</option>
                    <option value="Production">Production</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={actionDueDate}
                    onChange={(e) => setActionDueDate(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Verification Plan / Evidence</label>
                <input
                  type="text"
                  value={actionVerificationPlan}
                  onChange={(e) => setActionVerificationPlan(e.target.value)}
                  placeholder="e.g. Work order sign-off, SOP training sign-in sheet"
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingAction}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  {isSubmittingAction ? 'Adding...' : 'Add Action'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
