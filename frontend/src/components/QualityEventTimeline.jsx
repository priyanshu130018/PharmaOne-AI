import React from 'react';
import { 
  CheckCircle2, Clock, ShieldCheck, AlertTriangle, ArrowRight,
  FileText, Activity, Layers, Lock, Check
} from './icons.jsx';

export default function QualityEventTimeline({ 
  deviation, 
  linkedRecords, 
  onNavigate, 
  onRecordClick 
}) {
  const isClosed = (deviation?.status || '').toLowerCase() === 'closed';
  const hasInv = !!linkedRecords?.investigation;
  const isInvDone = linkedRecords?.investigation?.status === 'completed' || isClosed;
  const hasRca = !!linkedRecords?.root_cause?.is_confirmed || isClosed;
  const hasCapa = !!linkedRecords?.capa;
  const isCapaDone = linkedRecords?.capa?.status?.toLowerCase() === 'completed' || isClosed;
  const isEffDone = (linkedRecords?.effectiveness?.status || '').toLowerCase() === 'effective' || isClosed;
  const isReleased = (linkedRecords?.batch_release?.status || '').toUpperCase() === 'RELEASED';

  const timelineSteps = [
    {
      id: 'batch_started',
      number: 1,
      title: 'Batch API-2026-041 Started',
      detail: 'Paracetamol API synthesis initiated on Reactor R-101 (Recipe v4.2).',
      timestamp: '26 Sep 2026 • 08:00 UTC',
      status: 'Completed',
      badgeClass: 'bg-emerald-100 text-emerald-800',
      action: () => onRecordClick?.('batch', 'API-2026-041'),
      actionLabel: 'View Batch'
    },
    {
      id: 'ipc_excursion',
      number: 2,
      title: 'IPC Thermal Excursion Detected',
      detail: 'Step 3 Reaction: Temperature measured 84 °C (Approved spec 76–80 °C). Excursion sustained 18 min.',
      timestamp: '27 Sep 2026 • 10:15 UTC',
      status: 'OUT OF SPEC',
      badgeClass: 'bg-red-100 text-red-800 border border-red-200',
      action: () => onNavigate?.('batches', { batchNumber: 'API-2026-041' }),
      actionLabel: 'View IPC Log'
    },
    {
      id: 'deviation_logged',
      number: 3,
      title: 'Deviation DEV-2026-018 Intake',
      detail: 'Exothermic addition halted, emergency chilled-water bypass engaged, batch placed on hold.',
      timestamp: '27 Sep 2026 • 10:45 UTC',
      status: 'Recorded',
      badgeClass: 'bg-blue-100 text-blue-800',
      action: () => onRecordClick?.('deviation', 'DEV-2026-018'),
      actionLabel: 'Intake Record'
    },
    {
      id: 'ai_assessment',
      number: 4,
      title: 'AI Intake Risk Assessment',
      detail: 'Severity: Major • Initial Impact: Product Quality. Potential 4-aminophenol degradation risk evaluated.',
      timestamp: '27 Sep 2026 • 10:46 UTC',
      status: 'AI Draft / QA Verified',
      badgeClass: 'bg-purple-100 text-purple-800',
      action: null,
      actionLabel: null
    },
    {
      id: 'investigation',
      number: 5,
      title: 'Investigation INV-2026-012 Executed',
      detail: 'Cross-functional engineering inspection & SCADA review. 4 tasks completed and 3 evidence records verified.',
      timestamp: '28 Sep 2026 • 14:00 UTC',
      status: isInvDone ? 'Completed' : hasInv ? 'In Progress' : 'Pending',
      badgeClass: isInvDone ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800',
      action: () => onRecordClick?.('investigation', linkedRecords?.investigation?.reference || 'INV-2026-012'),
      actionLabel: 'View INV-2026-012'
    },
    {
      id: 'root_cause',
      number: 6,
      title: 'Root Cause RCA-2026-012 Confirmed',
      detail: '5 Whys concluded: Inadequate preventive-maintenance control for the cooling-valve actuator EQ-ACT-04.',
      timestamp: '29 Sep 2026 • 15:00 UTC',
      status: hasRca ? 'Confirmed' : 'Pending Review',
      badgeClass: hasRca ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800',
      action: () => onNavigate?.('root_cause', { deviationId: 'DEV-2026-018' }),
      actionLabel: 'View 5 Whys RCA'
    },
    {
      id: 'capa',
      number: 7,
      title: 'CAPA-2026-009 Established',
      detail: 'Corrective: Actuator overhaul & seal replacement (Completed). Preventive: SOP-014 PM-204 revision (Completed).',
      timestamp: '29 Sep 2026 • 16:30 UTC',
      status: isCapaDone ? 'Completed' : hasCapa ? 'In Progress' : 'Pending',
      badgeClass: isCapaDone ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800',
      action: () => onRecordClick?.('capa', 'CAPA-2026-009'),
      actionLabel: 'View CAPA-2026-009'
    },
    {
      id: 'effectiveness',
      number: 8,
      title: 'Effectiveness EFF-2026-009 Verified',
      detail: '5 consecutive batches (API-2026-042 to 046) monitored with zero recurrence. Temperature strictly within 76–80 °C.',
      timestamp: '30 Sep 2026 • 11:00 UTC',
      status: isEffDone ? 'Effective (5/5 Pass)' : 'Pending Monitoring',
      badgeClass: isEffDone ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800',
      action: () => onRecordClick?.('effectiveness', 'EFF-2026-009'),
      actionLabel: 'View EFF-2026-009'
    },
    {
      id: 'closure',
      number: 9,
      title: 'Deviation Formally Closed',
      detail: 'All 4 Quality Gates passed. Regulatory closure authorized under 21 CFR Part 11 audit compliance.',
      timestamp: isClosed ? '30 Sep 2026 • 14:00 UTC' : 'Pending Sign-Off',
      status: isClosed ? 'CLOSED (Read Only)' : 'Awaiting Closure',
      badgeClass: isClosed ? 'bg-emerald-100 text-emerald-800 font-bold' : 'bg-slate-100 text-slate-700',
      action: () => onNavigate?.('closure', { deviationId: 'DEV-2026-018' }),
      actionLabel: 'View Quality Closure'
    },
    {
      id: 'batch_release',
      number: 10,
      title: 'Batch Release BR-2026-041 Disposed',
      detail: 'Analytical testing compliant (purity 99.8%). QA Responsible Person authorizes final commercial release.',
      timestamp: isReleased ? '30 Sep 2026 • 14:30 UTC' : 'Pending Disposition',
      status: isReleased ? 'RELEASED' : 'Pending QA Disposition',
      badgeClass: isReleased ? 'bg-emerald-100 text-emerald-800 font-bold' : 'bg-amber-100 text-amber-800',
      action: () => onRecordClick?.('batch_release', 'BR-2026-041'),
      actionLabel: 'View BR-2026-041'
    }
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            Quality Event Lifecycle Timeline (21 CFR Part 11 Audit Trail)
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-500">
          Traceable Chain: DEV-2026-018 → BR-2026-041
        </span>
      </div>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
        {timelineSteps.map((step) => {
          const isPass = ['Completed', 'Recorded', 'AI Draft / QA Verified', 'Confirmed', 'Effective (5/5 Pass)', 'CLOSED (Read Only)', 'RELEASED'].includes(step.status);
          const isCurrent = step.status.includes('Progress') || step.status.includes('Awaiting');
          
          return (
            <div key={step.id} className="relative group">
              {/* Circle Marker */}
              <div className={`absolute -left-[23px] top-1 flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white shadow-xs ${
                step.status === 'OUT OF SPEC'
                  ? 'bg-red-500 ring-2 ring-red-200'
                  : isPass
                  ? 'bg-emerald-600 ring-2 ring-emerald-200'
                  : isCurrent
                  ? 'bg-blue-600 ring-2 ring-blue-200 animate-pulse'
                  : 'bg-slate-300'
              }`}>
                {isPass ? '✓' : step.number}
              </div>

              {/* Event Body */}
              <div className="rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-white hover:border-blue-200 p-3 transition shadow-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900">{step.title}</span>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${step.badgeClass}`}>
                      {step.status}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {step.timestamp}
                  </span>
                </div>

                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  {step.detail}
                </p>

                {step.action && (
                  <div className="mt-2 pt-2 border-t border-slate-100 flex justify-end">
                    <button
                      type="button"
                      onClick={step.action}
                      className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 group-hover:translate-x-0.5 transition"
                    >
                      <span>{step.actionLabel}</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
