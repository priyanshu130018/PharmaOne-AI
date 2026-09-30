import React, { useState, useEffect } from 'react';
import { 
  Building2, Package, ArrowRight, ExternalLink, RefreshCw, 
  CheckCircle2, ShieldCheck, Factory, Layers
} from './icons.jsx';
import { getSuppliers, getRawMaterials } from '../api/client';

export default function SupplierView({ onNavigate, onRecordClick }) {
  const [suppliers, setSuppliers] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getSuppliers(), getRawMaterials()])
      .then(([suppData, matData]) => {
        setSuppliers(suppData);
        setMaterials(matData);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-blue-100 text-blue-800 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5" />
              Qualified Suppliers & Raw Materials
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">Vendor Quality & Raw Material Lots</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track qualified upstream material lots directly linked to active batches and quality events.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Suppliers List */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Building2 className="w-5 h-5 text-blue-600" />
              Approved Suppliers
            </h2>

            <div className="space-y-3">
              {suppliers.map((s) => (
                <div key={s.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">{s.supplier_name}</span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                      {s.qualification_status || 'Approved'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Code: <strong className="text-slate-700">{s.supplier_code}</strong>
                    {s.country && ` • Location: ${s.country}`}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Raw Materials List */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Package className="w-5 h-5 text-indigo-600" />
              Raw Material Lots
            </h2>

            <div className="space-y-3">
              {materials.map((m) => (
                <div key={m.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{m.material_name}</span>
                      <span className="text-xs text-slate-500 block font-mono">Lot: {m.lot_number || 'AA-2026-088'}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                      {m.status || 'Approved'}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between">
                    <span className="text-xs text-slate-600">
                      Linked Batch: <strong>API-2026-041</strong>
                    </span>
                    <button
                      onClick={() => onRecordClick?.('batch', 'API-2026-041')}
                      className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                      <span>View Batch</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
