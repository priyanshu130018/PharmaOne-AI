import React, { useState, useEffect } from 'react';
import { 
  MessageSquareWarning, ArrowRight, ExternalLink, RefreshCw, 
  Layers, AlertTriangle, CheckCircle2, Package
} from './icons.jsx';
import { getComplaints } from '../api/client';

export default function ComplaintView({ onNavigate, onRecordClick }) {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getComplaints()
      .then(data => setComplaints(data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-amber-100 text-amber-800 flex items-center gap-1.5">
              <MessageSquareWarning className="w-3.5 h-3.5" />
              Customer Complaints
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">Quality Complaints Surveillance</h1>
          <p className="text-sm text-slate-500 mt-1">
            Post-market feedback linked to batch manufacturing and investigation records.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {complaints.map((c) => (
            <div key={c.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-3">
                  <span className="text-base font-bold text-slate-900">{c.complaint_number}</span>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                    {c.status}
                  </span>
                  <span className="text-xs text-slate-500">Received: {c.received_date || '2026-03-24'}</span>
                </div>
                <div className="text-xs text-slate-600 font-medium">
                  Product: <strong>{c.product_name}</strong>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Issue Description</h4>
                <p className="text-sm text-slate-800 bg-slate-50 p-3 rounded-lg border border-slate-200">
                  {c.issue_description}
                </p>
              </div>

              {/* Linked Quality Records */}
              <div className="pt-2">
                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Connected Records</h5>
                <div className="flex flex-wrap gap-3">
                  {c.batch_number && (
                    <button
                      onClick={() => onRecordClick?.('batch', c.batch_number)}
                      className="px-3 py-1.5 bg-blue-50 border border-blue-200 hover:border-blue-400 rounded-lg text-xs font-medium text-blue-700 flex items-center gap-1.5 transition"
                    >
                      <Package className="w-3.5 h-3.5" />
                      Batch: {c.batch_number}
                    </button>
                  )}

                  {c.deviation_number && (
                    <button
                      onClick={() => onRecordClick?.('deviation', c.deviation_number)}
                      className="px-3 py-1.5 bg-purple-50 border border-purple-200 hover:border-purple-400 rounded-lg text-xs font-medium text-purple-700 flex items-center gap-1.5 transition"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Deviation: {c.deviation_number}
                    </button>
                  )}

                  {c.investigation_number && (
                    <button
                      onClick={() => onRecordClick?.('investigation', c.investigation_number)}
                      className="px-3 py-1.5 bg-indigo-50 border border-indigo-200 hover:border-indigo-400 rounded-lg text-xs font-medium text-indigo-700 flex items-center gap-1.5 transition"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Investigation: {c.investigation_number}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}

          {complaints.length === 0 && (
            <div className="text-center py-12 text-slate-400 italic bg-white rounded-xl border border-slate-200">
              No complaint records found.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
