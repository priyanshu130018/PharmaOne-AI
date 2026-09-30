import React, { useState, useEffect } from 'react';
import { 
  FileText, CheckCircle2, Clock, AlertTriangle, ShieldCheck, 
  Sparkles, ArrowRight, Plus, ExternalLink, RefreshCw, Check, 
  X, AlertCircle, ChevronDown, ChevronRight, User, Calendar, BookOpen
} from './icons.jsx';
import { 
  getInvestigation, 
  updateInvestigationTask, 
  addInvestigationTask, 
  addInvestigationEvidence, 
  completeInvestigation, 
  aiSuggestInvestigationPlan,
  getDeviationLinkedRecords
} from '../api/client';
import LinkedRecordsBar from './LinkedRecordsBar';
import WorkflowStepper from './WorkflowStepper';

export default function InvestigationWorkspaceView({ 
  investigationId = 'INV-2026-012', 
  deviationId = 'DEV-2026-018',
  onNavigate,
  onRecordClick
}) {
  const [investigation, setInvestigation] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // AI Suggestion State
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [showAiModal, setShowAiModal] = useState(false);

  // Task form modal
  const [showAddTask, setShowAddTask] = useState(false);
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskOwner, setNewTaskOwner] = useState('QA');
  const [newTaskDueDate, setNewTaskDueDate] = useState('');

  // Evidence modal
  const [showAddEvidence, setShowAddEvidence] = useState(false);
  const [newEvTitle, setNewEvTitle] = useState('');
  const [newEvType, setNewEvType] = useState('Log');
  const [newEvSummary, setNewEvSummary] = useState('');

  // Complete Investigation modal
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [conclusionText, setConclusionText] = useState('');
  const [impactAssessmentText, setImpactAssessmentText] = useState('');
  const [submittingComplete, setSubmittingComplete] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const invData = await getInvestigation(investigationId);
      setInvestigation(invData);
      
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
      console.error('Failed to load investigation:', err);
      setError(err.message || 'Failed to load investigation record.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [investigationId]);

  const handleToggleTaskStatus = async (task) => {
    try {
      const nextStatus = task.status === 'Completed' ? 'In Progress' : 'Completed';
      await updateInvestigationTask(investigation.id, task.id, { status: nextStatus });
      setFeedback({ type: 'success', message: `Task status updated to "${nextStatus}".` });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to update task: ' + err.message });
    }
  };

  const handleAddTask = async (e) => {
    e.preventDefault();
    if (!newTaskDesc.trim()) return;
    try {
      await addInvestigationTask(investigation.id, {
        title: newTaskDesc,
        description: newTaskDesc,
        owner: newTaskOwner,
        due_date: newTaskDueDate || undefined,
        status: 'Pending'
      });
      setShowAddTask(false);
      setNewTaskDesc('');
      setFeedback({ type: 'success', message: 'Investigation task added successfully.' });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to add task: ' + err.message });
    }
  };

  const handleAddEvidence = async (e) => {
    e.preventDefault();
    if (!newEvTitle.trim()) return;
    try {
      await addInvestigationEvidence(investigation.id, {
        title: newEvTitle,
        evidence_type: newEvType,
        summary: newEvSummary,
        snippet: newEvSummary
      });
      setShowAddEvidence(false);
      setNewEvTitle('');
      setNewEvSummary('');
      setFeedback({ type: 'success', message: 'Evidence added to investigation.' });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to add evidence: ' + err.message });
    }
  };

  const handleRunAiSuggestion = async () => {
    try {
      setIsAiLoading(true);
      const suggestion = await aiSuggestInvestigationPlan(investigation.id, investigation.deviation_id || deviationId);
      setAiSuggestion(suggestion);
      setShowAiModal(true);
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to get AI recommendation: ' + err.message });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleAcceptAiPlan = async () => {
    if (!aiSuggestion) return;
    // Add suggested tasks to investigation
    const tasks = aiSuggestion.tasks_suggested || aiSuggestion.suggested_tasks || [];
    if (tasks.length) {
      for (const t of tasks) {
        try {
          const desc = t.description || t.title || (typeof t === 'string' ? t : 'AI Suggested Task');
          await addInvestigationTask(investigation.id, {
            title: desc,
            description: desc,
            owner: t.owner || 'QA',
            status: 'Pending'
          });
        } catch (e) {
          console.warn('Failed to add suggested task', e);
        }
      }
    }
    // Add suggested evidence references
    const evidence = aiSuggestion.evidence_suggested || aiSuggestion.evidence_to_review || [];
    if (evidence.length) {
      for (const ev of evidence) {
        try {
          const title = ev.title || (typeof ev === 'string' ? ev : 'Evidence Document');
          const summ = ev.summary || ev.snippet || ev.reason || 'AI identified relevant investigation record';
          await addInvestigationEvidence(investigation.id, {
            title: title,
            evidence_type: ev.evidence_type || ev.type || 'Document',
            summary: summ,
            snippet: summ
          });
        } catch (e) {
          console.warn('Failed to add suggested evidence', e);
        }
      }
    }
    setShowAiModal(false);
    setFeedback({ type: 'success', message: 'AI investigation plan applied successfully.' });
    fetchDetails();
  };

  const handleCompleteInvestigation = async () => {
    if (!conclusionText.trim()) {
      setFeedback({ type: 'error', message: 'Conclusion statement is required to complete the investigation.' });
      return;
    }
    try {
      setSubmittingComplete(true);
      await completeInvestigation(investigation.id, {
        conclusion: conclusionText,
        product_impact_assessment: impactAssessmentText || 'Product impact evaluated against acceptance criteria.'
      });
      setShowCompleteModal(false);
      setFeedback({ type: 'success', message: 'Investigation marked as Completed.' });
      fetchDetails();
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to complete investigation: ' + err.message });
    } finally {
      setSubmittingComplete(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-slate-600 font-medium">Loading Investigation Workspace...</div>
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl flex items-center space-x-3">
          <AlertCircle className="w-6 h-6 shrink-0" />
          <div>
            <h3 className="font-semibold text-lg">Investigation Not Found</h3>
            <p className="text-sm mt-1">{error || 'Unable to retrieve investigation record.'}</p>
          </div>
        </div>
      </div>
    );
  }

  const allTasksCompleted = investigation.tasks?.length > 0 && investigation.tasks.every(t => t.status === 'Completed');
  const isCompleted = investigation.status === 'Completed' || investigation.completed_at;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Linked Records Context Bar */}
      <LinkedRecordsBar 
        records={linkedRecords}
        activeType="investigation"
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

      {/* Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-3">
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-blue-100 text-blue-800">
              Investigation Workspace
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded ${
              isCompleted ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {investigation.status}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2 flex items-center gap-2">
            {investigation.investigation_number}: {investigation.title}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Linked Deviation: <button onClick={() => onRecordClick?.('deviation', deviationId)} className="text-blue-600 font-medium hover:underline">{deviationId}</button>
            {' • '}Assigned Investigator: <span className="font-medium text-slate-700">{investigation.assigned_investigator || 'QA Department'}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAiSuggestion}
            disabled={isAiLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition shadow-sm"
          >
            <Sparkles className={`w-4 h-4 ${isAiLoading ? 'animate-spin' : 'text-indigo-600'}`} />
            {isAiLoading ? 'Analyzing SOPs...' : 'Suggest Investigation Plan'}
          </button>

          {!isCompleted ? (
            <button
              onClick={() => {
                setConclusionText(investigation.conclusion || '');
                setImpactAssessmentText(investigation.product_impact_assessment || '');
                setShowCompleteModal(true);
              }}
              className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition"
            >
              <CheckCircle2 className="w-4 h-4" />
              Complete Investigation
            </button>
          ) : (
            <button
              onClick={() => onNavigate?.('root_cause', { deviationId, investigationId: investigation.investigation_number })}
              className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 shadow-sm transition"
            >
              <span>Proceed to 5 Whys Root Cause</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Workflow Stepper */}
      <WorkflowStepper currentStep={2} onStepClick={(step) => {
        if (step.id === 'reported') onNavigate?.('deviation_detail', { deviationId });
        if (step.id === 'investigation') { /* stay here */ }
        if (step.id === 'root_cause') onNavigate?.('root_cause', { deviationId, investigationId: investigation.investigation_number });
        if (step.id === 'capa') onNavigate?.('capa', { deviationId });
        if (step.id === 'effectiveness') onNavigate?.('effectiveness', { deviationId });
        if (step.id === 'closed') onNavigate?.('closure', { deviationId });
      }} />

      {/* Main Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Investigation Plan, Tasks & Analysis */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview & Plan Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <FileText className="w-5 h-5 text-blue-600" />
              Investigation Scope & Plan
            </h2>
            <div className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200">
              {investigation.investigation_plan || (
                <span className="text-slate-400 italic">No formal investigation plan recorded. Use the AI Quality Assistant to generate a compliant protocol.</span>
              )}
            </div>

            {investigation.product_impact_assessment && (
              <div className="mt-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Product Impact Assessment</h3>
                <div className="text-sm text-slate-800 bg-amber-50/60 border border-amber-200/80 p-3.5 rounded-lg">
                  {investigation.product_impact_assessment}
                </div>
              </div>
            )}

            {investigation.conclusion && (
              <div className="mt-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Investigation Conclusion</h3>
                <div className="text-sm text-slate-800 bg-emerald-50/60 border border-emerald-200/80 p-3.5 rounded-lg">
                  {investigation.conclusion}
                </div>
              </div>
            )}
          </div>

          {/* Investigation Tasks Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-blue-600" />
                  Investigation Action Tasks
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Track specific actions, evidence gathering, and technical interviews required for closure.
                </p>
              </div>
              <button
                onClick={() => setShowAddTask(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition"
              >
                <Plus className="w-4 h-4" />
                Add Task
              </button>
            </div>

            <div className="space-y-3">
              {investigation.tasks?.map((task, idx) => (
                <div 
                  key={task.id || idx}
                  className={`flex items-start justify-between p-3.5 rounded-lg border transition ${
                    task.status === 'Completed' 
                      ? 'bg-slate-50/70 border-slate-200' 
                      : 'bg-white border-blue-200 shadow-sm'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <button
                      onClick={() => handleToggleTaskStatus(task)}
                      className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center border transition ${
                        task.status === 'Completed'
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-slate-300 hover:border-blue-500 text-transparent'
                      }`}
                      title="Click to toggle status"
                    >
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </button>
                    <div>
                      <p className={`text-sm font-medium ${
                        task.status === 'Completed' ? 'line-through text-slate-400' : 'text-slate-800'
                      }`}>
                        {task.task_number ? `${task.task_number}. ` : ''}{task.description || task.title}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                        <span className="flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-slate-400" />
                          Owner: <strong className="text-slate-700">{task.owner}</strong>
                        </span>
                        {task.due_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            Due: {task.due_date}
                          </span>
                        )}
                        {task.notes && (
                          <span className="text-slate-500 italic">"{task.notes}"</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium shrink-0 ${
                    task.status === 'Completed'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}>
                    {task.status}
                  </span>
                </div>
              ))}

              {(!investigation.tasks || investigation.tasks.length === 0) && (
                <div className="text-center py-6 text-sm text-slate-400 italic bg-slate-50 rounded-lg">
                  No investigation tasks assigned yet. Click "Add Task" or use the AI Assistant to suggest tasks.
                </div>
              )}
            </div>
          </div>

          {/* Quick Root Cause Preview & Navigation */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/80 rounded-xl p-5 flex items-center justify-between">
            <div className="space-y-1">
              <h3 className="font-semibold text-slate-900 text-base flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-indigo-600" />
                Root Cause Analysis (5 Whys)
              </h3>
              <p className="text-xs text-slate-600 max-w-xl">
                {(investigation.root_cause_analysis?.final_root_cause || investigation.root_cause_analysis?.root_cause_summary || investigation.root_cause?.root_cause_summary) ? (
                  <span><strong>Identified Root Cause:</strong> {investigation.root_cause_analysis?.final_root_cause || investigation.root_cause_analysis?.root_cause_summary || investigation.root_cause?.root_cause_summary}</span>
                ) : (
                  <span>Conduct structured 5 Whys analysis to determine the primary failure mechanism before proceeding to CAPA.</span>
                )}
              </p>
            </div>
            <button
              onClick={() => onNavigate?.('root_cause', { deviationId, investigationId: investigation.investigation_number })}
              className="px-4 py-2 text-xs font-semibold text-indigo-700 bg-white border border-indigo-200 rounded-lg hover:bg-indigo-50 shadow-sm shrink-0 flex items-center gap-1.5 transition"
            >
              <span>Open 5 Whys Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right Col: Evidence & Reference SOPs */}
        <div className="space-y-6">
          {/* Evidence Repository Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                Attached Evidence
              </h2>
              <button
                onClick={() => setShowAddEvidence(true)}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" /> Attach
              </button>
            </div>

            <div className="space-y-3">
              {investigation.evidence?.map((item, idx) => (
                <div key={item.id || idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">{item.title}</span>
                    <span className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded text-[10px] font-medium">
                      {item.evidence_type}
                    </span>
                  </div>
                  {(item.summary || item.snippet) && (
                    <p className="text-slate-600">{item.summary || item.snippet}</p>
                  )}
                  {item.source && (
                    <span className="text-[10px] text-slate-400 block">Source: {item.source}</span>
                  )}
                </div>
              ))}

              {(!investigation.evidence || investigation.evidence.length === 0) && (
                <div className="text-xs text-slate-400 italic text-center py-4">
                  No evidence files attached yet.
                </div>
              )}
            </div>
          </div>

          {/* SOP-014 v3.2 Reference Guide */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Governing SOP Reference
              </h3>
              <span className="text-[11px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                v3.2 Effective
              </span>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-900">SOP-014: Chemical Synthesis & Reactor Temperature Control</h4>
              <p className="text-xs text-slate-600 mt-1">
                Section 4.2 specifies reactor temperature limit for Paracetamol Step 3 reaction at <strong>76–80 °C</strong>.
              </p>
            </div>
            <div className="bg-slate-50 p-3 rounded text-[11px] text-slate-600 space-y-1 border border-slate-200">
              <p>• Temperatures exceeding 82 °C for &gt;15 min trigger mandatory Quality Impact assessment.</p>
              <p>• Cooling valve actuators require monthly preventive maintenance inspection (Section 8.1).</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Suggestion Modal */}
      {showAiModal && aiSuggestion && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden border border-slate-200">
            <div className="p-5 border-b border-slate-200 bg-indigo-50/50 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <div>
                  <h3 className="font-bold text-slate-900">AI Quality Assistant: Investigation Plan</h3>
                  <p className="text-xs text-slate-500">Grounded in SOP-014 v3.2 & historical temperature excursions</p>
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
                  <strong>Advisory Only:</strong> Review each proposed task and evidence source. You must explicitly accept to add them to the investigation record.
                </span>
              </div>

              <div>
                <h4 className="font-semibold text-slate-800 mb-1">Recommended Investigation Plan</h4>
                <p className="text-slate-600 text-xs bg-slate-50 p-3 rounded border border-slate-200 leading-relaxed">
                  {aiSuggestion.investigation_plan}
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-slate-800 mb-1">Suggested Tasks ({(aiSuggestion.tasks_suggested || aiSuggestion.suggested_tasks)?.length || 0})</h4>
                <div className="space-y-1.5">
                  {(aiSuggestion.tasks_suggested || aiSuggestion.suggested_tasks)?.map((t, i) => (
                    <div key={i} className="text-xs p-2 bg-slate-50 rounded border border-slate-200 flex justify-between">
                      <span className="font-medium text-slate-800">{t.description || t.title || t}</span>
                      <span className="text-slate-500 font-semibold">{t.owner || 'QA'}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-slate-800 mb-1">Suggested Evidence Sources</h4>
                <div className="space-y-1.5">
                  {(aiSuggestion.evidence_suggested || aiSuggestion.evidence_to_review)?.map((ev, i) => (
                    <div key={i} className="text-xs p-2 bg-slate-50 rounded border border-slate-200">
                      <span className="font-semibold text-slate-800">{ev.title || ev}</span>
                      {(ev.reason || ev.summary || ev.snippet) && (
                        <p className="text-slate-500 text-[11px] mt-0.5">{ev.reason || ev.summary || ev.snippet}</p>
                      )}
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
                Reject / Close
              </button>
              <button
                onClick={handleAcceptAiPlan}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm"
              >
                Accept and Populate Tasks
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Task Modal */}
      {showAddTask && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <h3 className="font-bold text-slate-900 text-lg mb-4">Add Investigation Task</h3>
            <form onSubmit={handleAddTask} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Task Description *</label>
                <textarea
                  required
                  rows={3}
                  value={newTaskDesc}
                  onChange={(e) => setNewTaskDesc(e.target.value)}
                  placeholder="e.g. Interview shift supervisor regarding cooling valve manual override"
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Owner / Department</label>
                  <select
                    value={newTaskOwner}
                    onChange={(e) => setNewTaskOwner(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                  >
                    <option value="QA">QA</option>
                    <option value="Engineering">Engineering</option>
                    <option value="Production">Production</option>
                    <option value="QC">QC</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Target Due Date</label>
                  <input
                    type="date"
                    value={newTaskDueDate}
                    onChange={(e) => setNewTaskDueDate(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddTask(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Evidence Modal */}
      {showAddEvidence && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <h3 className="font-bold text-slate-900 text-lg mb-4">Attach Evidence Record</h3>
            <form onSubmit={handleAddEvidence} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Evidence Title *</label>
                <input
                  required
                  type="text"
                  value={newEvTitle}
                  onChange={(e) => setNewEvTitle(e.target.value)}
                  placeholder="e.g. SCADA Temperature Trend Chart"
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Evidence Type</label>
                <select
                  value={newEvType}
                  onChange={(e) => setNewEvType(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                >
                  <option value="Log">Log File</option>
                  <option value="Maintenance Record">Maintenance Record</option>
                  <option value="SOP Document">SOP Document</option>
                  <option value="Interview">Interview Notes</option>
                  <option value="Lab Result">Lab Analytical Result</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Summary / Context</label>
                <textarea
                  rows={2}
                  value={newEvSummary}
                  onChange={(e) => setNewEvSummary(e.target.value)}
                  placeholder="e.g. Confirms 84 °C spike at 14:22 for 18 min duration."
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddEvidence(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Attach Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Complete Investigation Modal */}
      {showCompleteModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 border border-slate-200">
            <h3 className="font-bold text-slate-900 text-lg mb-2">Complete Investigation</h3>
            <p className="text-xs text-slate-500 mb-4">
              Formal closure of investigation activities. This will unlock the Root Cause Analysis (5 Whys) stage.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Product Impact Assessment *</label>
                <textarea
                  rows={3}
                  value={impactAssessmentText}
                  onChange={(e) => setImpactAssessmentText(e.target.value)}
                  placeholder="e.g. Temperature excursion did not exceed degradation threshold; HPLC purity remains within 99.8% spec."
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Investigation Conclusion *</label>
                <textarea
                  required
                  rows={3}
                  value={conclusionText}
                  onChange={(e) => setConclusionText(e.target.value)}
                  placeholder="e.g. Root failure linked to cooling actuator degradation. Actuator replacement and revised PM scheduled."
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  disabled={submittingComplete}
                  onClick={() => setShowCompleteModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={submittingComplete}
                  onClick={handleCompleteInvestigation}
                  className="px-5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {submittingComplete ? 'Completing...' : 'Sign Off & Complete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
