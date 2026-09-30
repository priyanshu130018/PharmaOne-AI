import React from "react";

export default function LinkedRecordsBar({ 
  linkedRecords, 
  records, 
  onNavigate, 
  onRecordClick,
  activeType 
}) {
  const data = linkedRecords || records;
  if (!data) return null;

  const recordDefs = [
    { label: "Batch", key: "batch", icon: "📦" },
    { label: "Deviation", key: "deviation", icon: "⚠️" },
    { label: "Investigation", key: "investigation", icon: "🔍" },
    { label: "Root Cause", key: "root_cause", icon: "🎯" },
    { label: "CAPA", key: "capa", icon: "🛡️" },
    { label: "Effectiveness", key: "effectiveness", icon: "📊" },
    { label: "Batch Release", key: "batch_release", icon: "✅" },
    { label: "Complaint", key: "complaint", icon: "📋" },
    { label: "Supplier", key: "supplier", icon: "🏭" },
  ];

  // Only keep records that exist in data
  const existingItems = recordDefs.filter((def) => {
    const val = data[def.key];
    return val && (val.reference || val.id || val.title);
  });

  if (existingItems.length === 0) return null;

  const handleClick = (itemKey, record) => {
    if (onRecordClick) {
      onRecordClick(itemKey, record.id || record.reference);
      return;
    }
    if (onNavigate) {
      const targetMap = {
        batch: "batches",
        deviation: "deviations",
        investigation: "investigation",
        root_cause: "root_cause",
        capa: "capa",
        effectiveness: "effectiveness",
        batch_release: "batch_release",
        closure: "closure",
        closed: "closure",
        complaint: "complaints",
        supplier: "batches",
      };
      const targetView = targetMap[itemKey] || itemKey;
      const params = {};
      if (itemKey === "batch") params.batchNumber = record.reference || "API-2026-041";
      if (itemKey === "deviation" || itemKey === "closure" || itemKey === "closed") {
        params.deviationId = record.reference || record.id || "DEV-2026-018";
      }
      if (itemKey === "investigation" || itemKey === "root_cause") {
        params.investigationId = record.reference || record.id || "INV-2026-012";
        params.deviationId = "DEV-2026-018";
      }
      if (itemKey === "capa" || itemKey === "effectiveness") {
        params.capaId = record.reference || record.id || "CAPA-2026-009";
        params.deviationId = "DEV-2026-018";
      }
      if (itemKey === "batch_release") {
        params.batchNumber = "API-2026-041";
        params.batchReleaseId = record.reference || record.id || "BR-2026-041";
      }
      if (itemKey === "complaint") params.complaintNumber = record.reference || record.id;
      onNavigate(targetView, params);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 shadow-2xs text-xs">
      <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-slate-500 text-[10px] mr-1 shrink-0">
        <span className="text-blue-600">🔗</span>
        <span>Linked Context:</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {existingItems.map((item) => {
          const record = data[item.key];
          const isActive = activeType === item.key || (activeType === "closed" && item.key === "deviation");
          const refText = record.reference || record.id || record.title;

          return (
            <button
              key={item.key}
              type="button"
              onClick={() => handleClick(item.key, record)}
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors border ${
                isActive
                  ? "bg-blue-600 text-white border-blue-600 font-semibold shadow-2xs"
                  : "bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border-slate-200 hover:border-blue-300"
              }`}
            >
              <span className="text-xs">{item.icon}</span>
              <span className="font-semibold text-[11px]">{item.label}:</span>
              <span className="font-mono text-[11px] font-bold">{refText}</span>
              {record.status && (
                <span className={`text-[10px] px-1 py-0.2 rounded font-medium ${
                  isActive 
                    ? "bg-blue-500/80 text-white" 
                    : record.status.toLowerCase().includes("out") || record.status.toLowerCase().includes("warn")
                    ? "bg-red-100 text-red-700"
                    : record.status.toLowerCase().includes("closed") || record.status.toLowerCase().includes("effective") || record.status.toLowerCase().includes("released")
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-slate-200/80 text-slate-600"
                }`}>
                  {record.status}
                </span>
              )}
              <span className="text-[10px] font-bold opacity-70 ml-0.5">View →</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
