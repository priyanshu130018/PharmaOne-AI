import React, { useEffect, useState, useMemo } from "react";
import { api } from "../api/client.js";
import LinkedRecordsBar from "./LinkedRecordsBar.jsx";

export default function BatchModuleView({ 
  batchNumber: initialBatchNumber, 
  initialTab,
  onCreateDeviationFromIpc, 
  onNavigate,
  onRecordClick 
}) {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 4 Core Manufacturing Tabs: "batches" | "raw_materials" | "manufacturing_steps" | "in_process_checks"
  const getCleanTab = (tab) => {
    if (tab === "process_checks") return "in_process_checks";
    if (["batches", "raw_materials", "manufacturing_steps", "in_process_checks"].includes(tab)) return tab;
    return "batches";
  };
  const [activeTab, setActiveTab] = useState(() => getCleanTab(initialTab));

  // Search & Filters for Batches Table
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [qualityFilter, setQualityFilter] = useState("ALL");

  // Modals
  const [showCreateBatchModal, setShowCreateBatchModal] = useState(false);
  const [showAddStepModal, setShowAddStepModal] = useState(false);
  const [showAddIpcModal, setShowAddIpcModal] = useState(false);
  const [showAddRmModal, setShowAddRmModal] = useState(false);

  // New Batch Form State
  const [newBatchForm, setNewBatchForm] = useState({
    batch_number: "API-2026-055",
    product_name: "Ibuprofen API",
    product_code: "IBU-400",
    recipe_version: "v3.1",
    site_plant: "Bengaluru",
    status: "In Progress",
    manufacturing_date: new Date().toISOString().split("T")[0],
  });

  // New Step Form State
  const [newStepForm, setNewStepForm] = useState({
    step_number: 3,
    name: "Step 3 — Reaction",
    status: "in_progress",
    notes: "Reaction temperature limit 70–75°C",
  });

  // New IPC Form State
  const [newIpcForm, setNewIpcForm] = useState({
    parameter: "Temperature",
    spec_min: "70",
    spec_max: "75",
    actual_value: "79",
    unit: "°C",
    operator: "Operator K. Sharma",
    manufacturing_step_id: "",
  });

  // New Raw Material Form State
  const [newRmForm, setNewRmForm] = useState({
    name: "Isobutylbenzene",
    material_code: "RM-IBB-01",
    lot_number: "RM-2026-055",
    supplier_name: "ChemCorp",
    status: "Approved",
    batch_id: "",
  });

  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  // Load all batches
  const loadBatches = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listBatches();
      setBatches(data || []);
      
      // Determine selected batch: either match initialBatchNumber or default to API-2026-055 / API-2026-041 or first
      if (initialBatchNumber) {
        const found = (data || []).find(b => b.batch_number === initialBatchNumber || b.id === initialBatchNumber);
        if (found) {
          await loadBatchDetail(found.id);
          return;
        }
      }
      
      if (data && data.length > 0) {
        const defaultBatch = data.find(b => b.batch_number === "API-2026-055") || data.find(b => b.batch_number === "API-2026-041") || data[0];
        await loadBatchDetail(defaultBatch.id);
      }
    } catch (err) {
      setError(err.message || "Failed to load batches");
    } finally {
      setLoading(false);
    }
  };

  const loadBatchDetail = async (idOrNumber) => {
    try {
      setActionLoading(true);
      const detail = await api.getBatch(idOrNumber);
      setSelectedBatch(detail);
      if (detail?.manufacturing_steps?.length > 0) {
        setNewStepForm(prev => ({
          ...prev,
          step_number: detail.manufacturing_steps.length + 1
        }));
        setNewIpcForm(prev => ({
          ...prev,
          manufacturing_step_id: detail.manufacturing_steps[0].id
        }));
      }
    } catch (err) {
      setError(err.message || "Failed to load batch details");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    loadBatches();
  }, [initialBatchNumber]);

  // Filtered batches list
  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch = !q || 
        b.batch_number?.toLowerCase().includes(q) ||
        b.product_name?.toLowerCase().includes(q) ||
        b.recipe_version?.toLowerCase().includes(q) ||
        b.site_plant?.toLowerCase().includes(q);

      const matchesStatus = statusFilter === "ALL" || b.status === statusFilter;
      
      let matchesQuality = true;
      if (qualityFilter === "EXCURSION") {
        matchesQuality = b.batch_number === "API-2026-041" || (b.deviations && b.deviations.length > 0);
      } else if (qualityFilter === "NORMAL") {
        matchesQuality = b.batch_number !== "API-2026-041" && (!b.deviations || b.deviations.length === 0);
      }

      return matchesSearch && matchesStatus && matchesQuality;
    });
  }, [batches, searchQuery, statusFilter, qualityFilter]);

  // Handle Create Batch Submission
  const handleCreateBatch = async (e) => {
    e.preventDefault();
    if (!newBatchForm.batch_number.trim()) {
      alert("Batch Number is required");
      return;
    }
    try {
      setActionLoading(true);
      const created = await api.createBatch(newBatchForm);
      setShowCreateBatchModal(false);
      setActionMessage(`Batch ${created.batch_number} created successfully.`);
      setTimeout(() => setActionMessage(null), 4000);
      await loadBatches();
      await loadBatchDetail(created.id);
      setActiveTab("batches");
    } catch (err) {
      alert("Error creating batch: " + (err.message || err));
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Add Step
  const handleAddStep = async (e) => {
    e.preventDefault();
    if (!selectedBatch || !newStepForm.name.trim()) return;
    try {
      setActionLoading(true);
      await api.addManufacturingStep(selectedBatch.id, {
        step_number: parseInt(newStepForm.step_number, 10) || (selectedBatch.manufacturing_steps?.length || 0) + 1,
        name: newStepForm.name.trim(),
        status: newStepForm.status,
        warning_details: newStepForm.notes || undefined,
      });
      setShowAddStepModal(false);
      setActionMessage(`Step "${newStepForm.name}" added to Batch ${selectedBatch.batch_number}.`);
      setTimeout(() => setActionMessage(null), 4000);
      await loadBatchDetail(selectedBatch.id);
    } catch (err) {
      alert("Error adding step: " + (err.message || err));
    } finally {
      setActionLoading(false);
    }
  };

  // Live calculation of IPC status in modal
  const computedIpcStatus = useMemo(() => {
    const min = parseFloat(newIpcForm.spec_min);
    const max = parseFloat(newIpcForm.spec_max);
    const act = parseFloat(newIpcForm.actual_value);
    if (!isNaN(min) && !isNaN(max) && !isNaN(act)) {
      if (act < min || act > max) {
        return { isOol: true, label: "OUT-OF-LIMIT (OOL)", note: "Process Excursion" };
      }
      return { isOol: false, label: "PASS", note: "Within Approved Limits" };
    }
    return { isOol: false, label: "PASS", note: "Pending Evaluation" };
  }, [newIpcForm.spec_min, newIpcForm.spec_max, newIpcForm.actual_value]);

  // IPC Summary Statistics for Active Batch
  const ipcStats = useMemo(() => {
    const checks = selectedBatch?.in_process_checks || [];
    const total = checks.length;
    let ool = 0;
    let passed = 0;
    checks.forEach((c) => {
      const isOol =
        c.status === "OUT-OF-LIMIT (OOL)" ||
        c.status === "OUT OF SPEC" ||
        c.status?.toLowerCase().includes("out");
      if (isOol) ool++;
      else passed++;
    });
    return { total, passed, ool };
  }, [selectedBatch?.in_process_checks]);

  // Check if any IPC in active batch is OUT-OF-LIMIT
  const oolIpc = useMemo(() => {
    if (!selectedBatch?.in_process_checks) return null;
    return selectedBatch.in_process_checks.find(
      (c) =>
        c.status === "OUT-OF-LIMIT (OOL)" ||
        c.status === "OUT OF SPEC" ||
        c.status?.toLowerCase().includes("out")
    );
  }, [selectedBatch]);

  // Handle Add IPC
  const handleAddIpc = async (e) => {
    e.preventDefault();
    if (!selectedBatch || !newIpcForm.parameter.trim()) return;
    try {
      setActionLoading(true);
      const unitStr = newIpcForm.unit ? `${newIpcForm.unit}` : "°C";
      const specStr = `${newIpcForm.spec_min}–${newIpcForm.spec_max}${unitStr}`.trim();
      const actualStr = `${newIpcForm.actual_value}${unitStr}`.trim();
      const isOol = computedIpcStatus.isOol;
      const statusStr = isOol ? "OUT-OF-LIMIT (OOL)" : "PASS";

      await api.createProcessCheck(selectedBatch.id, {
        batch_id: selectedBatch.id,
        parameter: newIpcForm.parameter,
        specification: specStr,
        spec_min: parseFloat(newIpcForm.spec_min) || null,
        spec_max: parseFloat(newIpcForm.spec_max) || null,
        actual_value: actualStr,
        unit: unitStr,
        operator: newIpcForm.operator || "Operator K. Sharma",
        manufacturing_step_id: newIpcForm.manufacturing_step_id || undefined,
        status: statusStr,
      });

      setShowAddIpcModal(false);
      setActionMessage(`In-Process Check for ${newIpcForm.parameter} recorded (${statusStr}).`);
      setTimeout(() => setActionMessage(null), 4000);
      await loadBatchDetail(selectedBatch.id);
    } catch (err) {
      alert("Error recording IPC: " + (err.message || err));
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Add Raw Material
  const handleAddRawMaterial = async (e) => {
    e.preventDefault();
    if (!newRmForm.name.trim() || !newRmForm.lot_number.trim()) return;
    try {
      setActionLoading(true);
      await api.createRawMaterial({
        name: newRmForm.name.trim(),
        material_code: newRmForm.material_code || undefined,
        lot_number: newRmForm.lot_number.trim(),
        supplier_name: newRmForm.supplier_name || "ChemCorp",
        status: newRmForm.status || "Approved",
        batch_id: selectedBatch ? selectedBatch.id : undefined,
      });
      setShowAddRmModal(false);
      setActionMessage(`Raw Material "${newRmForm.name}" added to Batch ${selectedBatch?.batch_number}.`);
      setTimeout(() => setActionMessage(null), 4000);
      if (selectedBatch) {
        await loadBatchDetail(selectedBatch.id);
      }
      await loadBatches();
    } catch (err) {
      alert("Error adding raw material: " + (err.message || err));
    } finally {
      setActionLoading(false);
    }
  };

  // Trigger deviation intake from Out-of-Limit IPC with ALL fields fully populated
  const handleCreateDeviation = (ipc) => {
    if (!selectedBatch) return;

    // Resolve associated manufacturing step
    const step = (selectedBatch.manufacturing_steps || []).find(
      (s) => s.id === (ipc.manufacturing_step_id || ipc.step_id)
    ) || selectedBatch.manufacturing_steps?.[0];

    const stepName = step?.name || "Step 3 — Reaction";
    const rawMaterialName = selectedBatch.raw_materials?.[0]?.name || "Isobutylbenzene";
    const processOp = stepName.includes("—") ? stepName.split("—")[1].trim() : stepName.includes("-") ? stepName.split("-")[1].trim() : "Reaction";
    const actualStr = ipc.actual_value.includes("°C") || ipc.actual_value.includes(ipc.unit || "") ? ipc.actual_value : `${ipc.actual_value}${ipc.unit || '°C'}`;
    const specStr = ipc.specification.includes("°C") || ipc.specification.includes(ipc.unit || "") ? ipc.specification : `${ipc.specification}${ipc.unit || '°C'}`;
    const operator = ipc.checked_by || ipc.operator || "Operator K. Sharma";
    const today = new Date().toISOString().split("T")[0];

    const payload = {
      batch_id: selectedBatch.id,
      batch_number: selectedBatch.batch_number,
      product_name: selectedBatch.product_name,
      recipe_version: selectedBatch.recipe_version,
      site_plant: selectedBatch.site_plant || "Bengaluru",
      raw_materials: selectedBatch.raw_materials || [],
      raw_material_name: rawMaterialName,
      manufacturing_step_id: step?.id,
      manufacturing_stage: stepName,
      process_operation: processOp,
      equipment: "Reactor R-101",
      department: "API Manufacturing",
      in_process_check_id: ipc.id,
      parameter: ipc.parameter || "Temperature",
      expected_condition: specStr,
      actual_condition: actualStr,
      duration: "15 minutes",
      reported_by: operator,
      source: "manufacturing",
      deviation_type: "process",
      severity: "major",
      impact: "product_quality",
      batch_status: "quarantined",
      immediate_action: `During manufacturing of Batch ${selectedBatch.batch_number} at ${stepName}, reaction heating was immediately paused, cooling applied, and QA notified. Batch quarantined pending QA investigation.`,
      qa_notified: true,
      occurred_on: today,
      title: `${ipc.parameter || 'Temperature'} process excursion on Batch ${selectedBatch.batch_number} at ${stepName}`,
      description: `During manufacturing of Batch ${selectedBatch.batch_number} at ${stepName}, ${(ipc.parameter || 'temperature').toLowerCase()} reached ${actualStr}, exceeding the approved process limit of ${specStr}.`,
    };

    if (onCreateDeviationFromIpc) {
      onCreateDeviationFromIpc(payload);
    } else if (onNavigate) {
      onNavigate("deviations", payload);
    }
  };

  // Linked records configuration
  const linkedRecords = useMemo(() => {
    if (!selectedBatch) return null;
    const isCanonical = selectedBatch.batch_number === "API-2026-041";
    return {
      batch: {
        reference: selectedBatch.batch_number,
        title: `${selectedBatch.product_name} (${selectedBatch.recipe_version})`,
        status: selectedBatch.status,
        id: selectedBatch.id,
      },
      deviation: isCanonical ? {
        reference: "DEV-2026-018",
        title: "Reactor temperature exceeded limit",
        status: "Under Investigation",
      } : selectedBatch.linked_deviation_references?.length > 0 ? {
        reference: selectedBatch.linked_deviation_references[0],
        title: "Process excursion deviation",
        status: "Open",
      } : null,
      investigation: isCanonical ? {
        reference: "INV-2026-012",
        title: "Cooling actuator response lag",
        status: "Root Cause",
      } : null,
      capa: isCanonical ? {
        reference: "CAPA-2026-009",
        title: "Actuator overhaul & PM revision",
        status: "In Progress",
      } : null,
      batch_release: {
        reference: isCanonical ? "BR-2026-041" : `BR-${selectedBatch.batch_number}`,
        title: "QA Disposition",
        status: selectedBatch.release_status || "Pending",
      },
      supplier: {
        reference: "ChemCorp",
        title: "Approved RM Vendor",
        status: "Qualified",
      },
    };
  }, [selectedBatch]);

  return (
    <div className="space-y-4">
      {/* Top Workspace Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 sm:p-5 shadow-2xs">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Manufacturing & In-Process Control
            </h1>
            <span className="rounded bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 border border-blue-200">
              MES · Electronic Batch Records
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Batch-centered manufacturing flow: Batches → Raw Materials → Manufacturing Steps → In-Process Checks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setNewBatchForm({
                batch_number: "API-2026-055",
                product_name: "Ibuprofen API",
                product_code: "IBU-400",
                recipe_version: "v3.1",
                site_plant: "Bengaluru",
                status: "In Progress",
                manufacturing_date: new Date().toISOString().split("T")[0],
              });
              setShowCreateBatchModal(true);
            }}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 transition"
          >
            <span>+ Create Batch</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800 animate-fade-in">
          ✓ {actionMessage}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* ALWAYS CLEAR BANNER: WORKING ON BATCH: API-2026-055 | Product: Ibuprofen API | Recipe: v3.1 */}
      {selectedBatch ? (
        <div 
          data-testid="active-batch-banner"
          className="rounded-xl border border-blue-300 bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white p-4 sm:p-5 shadow-xs flex flex-wrap items-center justify-between gap-4"
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-200">
                ACTIVE WORKSPACE
              </span>
            </div>
            <div className="text-lg sm:text-xl font-bold font-mono tracking-tight text-white mt-0.5">
              WORKING ON BATCH: {selectedBatch.batch_number}
            </div>
            <div className="text-xs sm:text-sm text-blue-100 font-medium mt-1">
              Product: <span className="font-semibold text-white">{selectedBatch.product_name}</span> | Recipe: <span className="font-mono text-white">{selectedBatch.recipe_version}</span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-blue-800/90 border border-blue-400/40 px-3 py-1 text-xs font-semibold text-blue-100">
              Site: {selectedBatch.site_plant || "Bengaluru"}
            </span>
            <span className="rounded-full bg-blue-800/90 border border-blue-400/40 px-3 py-1 text-xs font-semibold text-blue-100">
              Status: {selectedBatch.status}
            </span>
            <span className="rounded-full bg-indigo-800/90 border border-indigo-400/40 px-3 py-1 text-xs font-semibold text-indigo-100">
              QA Release: {selectedBatch.release_status || "Pending"}
            </span>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-center text-xs text-slate-500">
          No batch selected. Please select a batch below to open as the active workspace.
        </div>
      )}

      {/* 4 CORE TABS: Batches | Raw Materials | Manufacturing Steps | In-Process Checks */}
      <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 pt-2 rounded-t-xl overflow-x-auto shadow-2xs">
        <button
          type="button"
          data-testid="tab-batches"
          onClick={() => setActiveTab("batches")}
          className={`pb-2.5 px-3 text-xs font-bold transition border-b-2 flex items-center gap-2 whitespace-nowrap cursor-pointer ${
            activeTab === "batches"
              ? "border-blue-600 text-blue-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <span>📦 Batches</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
            {batches.length}
          </span>
        </button>

        <button
          type="button"
          data-testid="tab-raw_materials"
          onClick={() => setActiveTab("raw_materials")}
          className={`pb-2.5 px-3 text-xs font-bold transition border-b-2 flex items-center gap-2 whitespace-nowrap cursor-pointer ${
            activeTab === "raw_materials"
              ? "border-blue-600 text-blue-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <span>🧪 Raw Materials</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
            {selectedBatch?.raw_materials?.length || 0}
          </span>
        </button>

        <button
          type="button"
          data-testid="tab-manufacturing_steps"
          onClick={() => setActiveTab("manufacturing_steps")}
          className={`pb-2.5 px-3 text-xs font-bold transition border-b-2 flex items-center gap-2 whitespace-nowrap cursor-pointer ${
            activeTab === "manufacturing_steps"
              ? "border-blue-600 text-blue-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <span>⚙️ Manufacturing Steps</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
            {selectedBatch?.manufacturing_steps?.length || 0}
          </span>
        </button>

        <button
          type="button"
          data-testid="tab-in_process_checks"
          onClick={() => setActiveTab("in_process_checks")}
          className={`pb-2.5 px-3 text-xs font-bold transition border-b-2 flex items-center gap-2 whitespace-nowrap cursor-pointer ${
            activeTab === "in_process_checks" || activeTab === "process_checks"
              ? "border-blue-600 text-blue-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <span>🌡️ In-Process Checks</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
            {selectedBatch?.in_process_checks?.length || 0}
          </span>
          {ipcStats.ool > 0 && (
            <span className="rounded-full bg-red-100 px-1.5 py-0.2 text-[9px] font-bold text-red-700 border border-red-200">
              {ipcStats.ool} OOL
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: BATCHES VIEW */}
      {activeTab === "batches" && (
        <div className="space-y-5">
          {/* Batches Search & Filters */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex-1 min-w-[240px]">
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search batch number, product, recipe..."
                    className="w-full rounded-lg border border-slate-300 bg-slate-50/50 py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none"
                  />
                  <span className="absolute left-2.5 top-2 text-slate-400 text-xs">🔍</span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Completed">Completed</option>
                  <option value="Quarantined">Quarantined</option>
                </select>

                <select
                  value={qualityFilter}
                  onChange={(e) => setQualityFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
                >
                  <option value="ALL">All Quality Statuses</option>
                  <option value="NORMAL">Normal</option>
                  <option value="EXCURSION">Process Excursion / Under Investigation</option>
                </select>

                <button
                  type="button"
                  onClick={() => {
                    setNewBatchForm({
                      batch_number: "API-2026-055",
                      product_name: "Ibuprofen API",
                      product_code: "IBU-400",
                      recipe_version: "v3.1",
                      site_plant: "Bengaluru",
                      status: "In Progress",
                      manufacturing_date: new Date().toISOString().split("T")[0],
                    });
                    setShowCreateBatchModal(true);
                  }}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 transition"
                >
                  + Create Batch
                </button>
              </div>
            </div>

            {/* Batches Table */}
            <div className="mt-3.5 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="py-2.5 px-3">Batch Number</th>
                    <th className="py-2.5 px-3">Product</th>
                    <th className="py-2.5 px-3">Recipe / Version</th>
                    <th className="py-2.5 px-3">Site / Plant</th>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Mfg Status</th>
                    <th className="py-2.5 px-3">Quality Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredBatches.map((b) => {
                    const isSelected = selectedBatch?.id === b.id;
                    const isExcursion = b.batch_number === "API-2026-041" || (b.deviations && b.deviations.length > 0);

                    return (
                      <tr
                        key={b.id}
                        onClick={() => loadBatchDetail(b.id)}
                        className={`cursor-pointer transition ${
                          isSelected
                            ? "bg-blue-50/80 font-semibold ring-1 ring-blue-300"
                            : "hover:bg-slate-50/70"
                        }`}
                      >
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                          {b.batch_number}
                          {isSelected && (
                            <span className="ml-1.5 text-[10px] text-blue-600 font-bold">● Active</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-800">
                          {b.product_name}
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">
                          {b.recipe_version}
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">
                          {b.site_plant}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px]">
                          {b.created_at ? new Date(b.created_at).toLocaleDateString() : "2026-09-30"}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            b.status === "In Progress"
                              ? "bg-blue-50 text-blue-700 border border-blue-200"
                              : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          }`}>
                            {b.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {isExcursion ? (
                            <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-300">
                              ⚠️ Excursion / Investigation
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                              ✓ Normal
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              loadBatchDetail(b.id);
                            }}
                            className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline"
                          >
                            Open Workspace →
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {filteredBatches.length === 0 && (
                    <tr>
                      <td colSpan="8" className="py-6 text-center text-xs text-slate-400">
                        No batches match the selected criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* ACTIVE BATCH WORKSPACE OVERVIEW */}
          {selectedBatch && (
            <div className="space-y-4 rounded-2xl border border-blue-100 bg-slate-50/50 p-4 sm:p-5 shadow-2xs">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
                <div>
                  <h3 className="font-mono text-base font-bold text-slate-900">
                    Active Batch Overview: {selectedBatch.batch_number}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Use the tabs above to manage Raw Materials, Manufacturing Steps, and In-Process Checks for this batch.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setActiveTab("raw_materials")}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Raw Materials ({selectedBatch.raw_materials?.length || 0}) →
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("manufacturing_steps")}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Steps ({selectedBatch.manufacturing_steps?.length || 0}) →
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("in_process_checks")}
                    className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-bold text-white hover:bg-blue-700"
                  >
                    IPC Checks ({selectedBatch.in_process_checks?.length || 0}) →
                  </button>
                </div>
              </div>

              {/* Linked Records Bar */}
              {linkedRecords && (
                <LinkedRecordsBar
                  linkedRecords={linkedRecords}
                  onNavigate={onNavigate}
                  onRecordClick={onRecordClick}
                  activeType="batch"
                />
              )}

              {/* Batch Detail Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Batch Number</div>
                  <div className="mt-1 font-mono text-sm font-bold text-slate-900">{selectedBatch.batch_number}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Product Name</div>
                  <div className="mt-1 text-xs font-semibold text-slate-900 truncate" title={selectedBatch.product_name}>{selectedBatch.product_name}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Master Recipe</div>
                  <div className="mt-1 font-mono text-xs font-semibold text-slate-900">{selectedBatch.recipe_version}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Site / Plant</div>
                  <div className="mt-1 text-xs font-semibold text-slate-900">{selectedBatch.site_plant}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Batch Status</div>
                  <div className="mt-1 text-xs font-semibold text-blue-700">{selectedBatch.status}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Release Disposition</div>
                  <div className="mt-1 text-xs font-semibold text-amber-700">{selectedBatch.release_status || "Pending QA Review"}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: RAW MATERIALS (ONLY FOR ACTIVE BATCH) */}
      {activeTab === "raw_materials" && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Raw Materials Charged — Batch {selectedBatch?.batch_number}
              </h2>
              <p className="text-[11px] text-slate-400">
                Showing ONLY raw materials assigned to active batch {selectedBatch?.batch_number} with verified supplier lot numbers.
              </p>
            </div>
            <button
              type="button"
              disabled={!selectedBatch}
              onClick={() => {
                setNewRmForm({
                  name: "Isobutylbenzene",
                  material_code: "RM-IBB-01",
                  lot_number: `RM-2026-${String(Math.floor(Math.random() * 900) + 100)}`,
                  supplier_name: "ChemCorp",
                  status: "Approved",
                  batch_id: selectedBatch ? selectedBatch.id : "",
                });
                setShowAddRmModal(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-blue-700 transition disabled:opacity-50"
            >
              <span>+ Add Raw Material</span>
            </button>
          </div>

          {selectedBatch?.raw_materials && selectedBatch.raw_materials.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="py-2.5 px-3">Material Name</th>
                    <th className="py-2.5 px-3">Material Code</th>
                    <th className="py-2.5 px-3">Lot Number</th>
                    <th className="py-2.5 px-3">Supplier</th>
                    <th className="py-2.5 px-3">Assigned Batch</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {selectedBatch.raw_materials.map((rm, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70 transition">
                      <td className="py-2.5 px-3 font-semibold text-slate-900">{rm.name}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">{rm.material_code || "—"}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-800">{rm.lot_number}</td>
                      <td className="py-2.5 px-3 text-slate-700">{rm.supplier_name || "ChemCorp"}</td>
                      <td className="py-2.5 px-3 font-mono text-blue-600 font-semibold">{selectedBatch.batch_number}</td>
                      <td className="py-2.5 px-3">
                        <span className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                          {rm.status || "Approved"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center space-y-2">
              <p className="text-xs font-semibold text-slate-600">
                No raw materials charged for Batch {selectedBatch?.batch_number} yet.
              </p>
              <p className="text-[11px] text-slate-400">
                Click "+ Add Raw Material" to charge verified ingredients (e.g. Isobutylbenzene) into this batch.
              </p>
              <button
                type="button"
                onClick={() => {
                  setNewRmForm({
                    name: "Isobutylbenzene",
                    material_code: "RM-IBB-01",
                    lot_number: "RM-2026-055",
                    supplier_name: "ChemCorp",
                    status: "Approved",
                    batch_id: selectedBatch ? selectedBatch.id : "",
                  });
                  setShowAddRmModal(true);
                }}
                className="mt-2 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
              >
                + Add Raw Material
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: MANUFACTURING STEPS (ONLY FOR ACTIVE BATCH) */}
      {activeTab === "manufacturing_steps" && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Manufacturing Execution Steps — Batch {selectedBatch?.batch_number}
              </h2>
              <p className="text-[11px] text-slate-400">
                Showing ONLY recipe progression steps belonging to active batch {selectedBatch?.batch_number}.
              </p>
            </div>
            <button
              type="button"
              disabled={!selectedBatch}
              onClick={() => {
                setNewStepForm({
                  step_number: (selectedBatch?.manufacturing_steps?.length || 0) + 1,
                  name: `Step ${(selectedBatch?.manufacturing_steps?.length || 0) + 1} — Reaction`,
                  status: "in_progress",
                  notes: "Reaction temperature limit 70–75°C",
                });
                setShowAddStepModal(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-blue-700 transition disabled:opacity-50"
            >
              <span>+ Add Manufacturing Step</span>
            </button>
          </div>

          {selectedBatch?.manufacturing_steps && selectedBatch.manufacturing_steps.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {selectedBatch.manufacturing_steps.map((step) => {
                const isWarning = step.status === "warning";
                const isCompleted = step.status === "completed";

                return (
                  <div
                    key={step.id}
                    className={`rounded-xl border p-4 transition shadow-2xs ${
                      isWarning
                        ? "border-amber-300 bg-amber-50/50 ring-1 ring-amber-200"
                        : isCompleted
                        ? "border-slate-200 bg-white"
                        : "border-slate-200 bg-slate-50/70"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                          Step {step.step_number}
                        </span>
                        <span className="text-xs font-bold text-slate-900">{step.name}</span>
                      </div>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        isWarning
                          ? "bg-amber-100 text-amber-800 border border-amber-300"
                          : isCompleted
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-slate-100 text-slate-600"
                      }`}>
                        {isWarning ? "⚠️ Warning" : isCompleted ? "✓ Completed" : step.status}
                      </span>
                    </div>
                    {step.warning_details && (
                      <div className="mt-2 rounded-lg border border-amber-200 bg-white p-2 text-[11px] text-amber-900">
                        <span className="font-semibold text-amber-800">Process Note: </span>
                        {step.warning_details}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center space-y-2">
              <p className="text-xs font-semibold text-slate-600">
                No manufacturing steps recorded for Batch {selectedBatch?.batch_number} yet.
              </p>
              <p className="text-[11px] text-slate-400">
                Click "+ Add Manufacturing Step" to create steps (e.g. Step 3 — Reaction) for this batch.
              </p>
              <button
                type="button"
                onClick={() => {
                  setNewStepForm({
                    step_number: 3,
                    name: "Step 3 — Reaction",
                    status: "in_progress",
                    notes: "Reaction temperature limit 70–75°C",
                  });
                  setShowAddStepModal(true);
                }}
                className="mt-2 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
              >
                + Add Manufacturing Step
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: IN-PROCESS CHECKS (ONLY FOR ACTIVE BATCH) */}
      {(activeTab === "in_process_checks" || activeTab === "process_checks") && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                In-Process Checks (IPC) — Batch {selectedBatch?.batch_number}
              </h2>
              <p className="text-[11px] text-slate-400">
                Quality control checks recorded for specific manufacturing steps on active batch {selectedBatch?.batch_number}.
              </p>
            </div>
            <button
              type="button"
              disabled={!selectedBatch}
              onClick={() => {
                if (selectedBatch?.manufacturing_steps?.length > 0) {
                  setNewIpcForm(prev => ({
                    ...prev,
                    manufacturing_step_id: selectedBatch.manufacturing_steps[0].id
                  }));
                }
                setShowAddIpcModal(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-blue-700 transition disabled:opacity-50"
            >
              <span>+ Add In-Process Check</span>
            </button>
          </div>

          {/* SIMPLE IPC REPORT FOR THE ACTIVE BATCH: Total checks / Passed / OOL */}
          <div data-testid="ipc-summary-report" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Total Checks</span>
                <span className="text-xl font-bold font-mono text-slate-900">{ipcStats.total}</span>
              </div>
              <span className="rounded-full bg-slate-200/70 px-2.5 py-1 text-xs font-bold text-slate-700">
                Batch {selectedBatch?.batch_number}
              </span>
            </div>

            <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3.5 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">Passed</span>
                <span className="text-xl font-bold font-mono text-emerald-700">{ipcStats.passed}</span>
              </div>
              <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800">
                ✓ In Spec
              </span>
            </div>

            <div className={`rounded-xl border p-3.5 flex items-center justify-between ${
              ipcStats.ool > 0
                ? "border-red-300 bg-red-50/80 ring-1 ring-red-200"
                : "border-slate-200 bg-slate-50/70"
            }`}>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-red-800 block">OUT-OF-LIMIT (OOL)</span>
                <span className="text-xl font-bold font-mono text-red-700">{ipcStats.ool}</span>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                ipcStats.ool > 0 ? "bg-red-600 text-white" : "bg-slate-200 text-slate-600"
              }`}>
                {ipcStats.ool > 0 ? "⚠️ Excursion Detected" : "0 OOL"}
              </span>
            </div>
          </div>

          {/* Out-of-Limit Excursion Banner if OOL detected */}
          {oolIpc && (
            <div className="rounded-xl border border-red-300 bg-red-50 p-4 flex flex-wrap items-center justify-between gap-3 shadow-xs">
              <div className="flex items-center gap-3">
                <span className="text-2xl">⚠️</span>
                <div>
                  <div className="text-xs font-bold text-red-900 uppercase tracking-wide">
                    Out-of-limit process excursion detected on Batch {selectedBatch?.batch_number}
                  </div>
                  <div className="text-xs text-red-800 mt-0.5">
                    {oolIpc.parameter}: recorded <span className="font-mono font-bold">{oolIpc.actual_value}</span> (Approved Process Limit: {oolIpc.specification}). Exceeds approved specification window.
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleCreateDeviation(oolIpc)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-red-700 transition"
              >
                <span>Create Deviation for Batch {selectedBatch?.batch_number} →</span>
              </button>
            </div>
          )}

          {/* IPC Table */}
          {selectedBatch?.in_process_checks && selectedBatch.in_process_checks.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="py-2.5 px-3">Manufacturing Step</th>
                    <th className="py-2.5 px-3">Parameter</th>
                    <th className="py-2.5 px-3">Approved Limit</th>
                    <th className="py-2.5 px-3">Actual Value Recorded</th>
                    <th className="py-2.5 px-3">Result</th>
                    <th className="py-2.5 px-3">Operator</th>
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {selectedBatch.in_process_checks.map((ipc) => {
                    const isOol =
                      ipc.status === "OUT-OF-LIMIT (OOL)" ||
                      ipc.status === "OUT OF SPEC" ||
                      ipc.status?.toLowerCase().includes("out");

                    const step = (selectedBatch.manufacturing_steps || []).find(
                      (s) => s.id === (ipc.manufacturing_step_id || ipc.step_id)
                    );
                    const stepName = step?.name || "Step 3 — Reaction";

                    return (
                      <tr
                        key={ipc.id}
                        className={isOol ? "bg-red-50/40 hover:bg-red-50/70 transition" : "hover:bg-slate-50/60 transition"}
                      >
                        <td className="py-2.5 px-3 font-semibold text-slate-900">
                          {stepName}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-800">
                          {ipc.parameter}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-600">
                          {ipc.specification}
                        </td>
                        <td className={`py-2.5 px-3 font-mono font-bold ${isOol ? "text-red-700 text-sm" : "text-slate-800"}`}>
                          {ipc.actual_value}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            isOol
                              ? "bg-red-100 text-red-800 border border-red-200 ring-2 ring-red-100"
                              : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          }`}>
                            {isOol ? "OUT-OF-LIMIT (OOL)" : "PASS"}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 font-medium">
                          {ipc.checked_by || ipc.operator || "Operator K. Sharma"}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                          {ipc.checked_at ? new Date(ipc.checked_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "14:15"}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          {isOol ? (
                            <button
                              type="button"
                              onClick={() => handleCreateDeviation(ipc)}
                              className="inline-flex items-center gap-1 rounded bg-red-600 px-2.5 py-1 text-xs font-bold text-white shadow-xs hover:bg-red-700 transition"
                            >
                              <span>Create Deviation for Batch {selectedBatch.batch_number}</span>
                            </button>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Within Limit</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center space-y-2">
              <p className="text-xs font-semibold text-slate-600">
                No in-process checks recorded for Batch {selectedBatch?.batch_number} yet.
              </p>
              <p className="text-[11px] text-slate-400">
                Click "+ Add In-Process Check" to record temperature, pH, or critical parameters against approved recipe limits.
              </p>
              <button
                type="button"
                onClick={() => {
                  if (selectedBatch?.manufacturing_steps?.length > 0) {
                    setNewIpcForm(prev => ({
                      ...prev,
                      manufacturing_step_id: selectedBatch.manufacturing_steps[0].id
                    }));
                  }
                  setShowAddIpcModal(true);
                }}
                className="mt-2 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
              >
                + Add In-Process Check
              </button>
            </div>
          )}
        </div>
      )}

      {/* MODAL: CREATE BATCH */}
      {showCreateBatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-2xs">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Create New Manufacturing Batch</h3>
                <p className="text-xs text-slate-500">Persisted directly in Supabase with electronic audit trail logging.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateBatchModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateBatch} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Batch Number *</label>
                  <input
                    type="text"
                    required
                    value={newBatchForm.batch_number}
                    onChange={(e) => setNewBatchForm(prev => ({ ...prev, batch_number: e.target.value }))}
                    placeholder="e.g. API-2026-055"
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Product *</label>
                  <input
                    type="text"
                    required
                    value={newBatchForm.product_name}
                    onChange={(e) => setNewBatchForm(prev => ({ ...prev, product_name: e.target.value }))}
                    placeholder="e.g. Ibuprofen API"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Recipe / Version *</label>
                  <input
                    type="text"
                    required
                    value={newBatchForm.recipe_version}
                    onChange={(e) => setNewBatchForm(prev => ({ ...prev, recipe_version: e.target.value }))}
                    placeholder="e.g. v3.1"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Site / Plant *</label>
                  <input
                    type="text"
                    required
                    value={newBatchForm.site_plant}
                    onChange={(e) => setNewBatchForm(prev => ({ ...prev, site_plant: e.target.value }))}
                    placeholder="e.g. Bengaluru"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Manufacturing Date</label>
                  <input
                    type="date"
                    value={newBatchForm.manufacturing_date}
                    onChange={(e) => setNewBatchForm(prev => ({ ...prev, manufacturing_date: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Manufacturing Status</label>
                  <select
                    value={newBatchForm.status}
                    onChange={(e) => setNewBatchForm(prev => ({ ...prev, status: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  >
                    <option value="In Progress">In Progress</option>
                    <option value="Completed">Completed</option>
                    <option value="Quarantined">Quarantined</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateBatchModal(false)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? "Saving to Supabase..." : "Create Batch"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD MANUFACTURING STEP */}
      {showAddStepModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-2xs">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Add Manufacturing Step</h3>
                <p className="text-xs text-slate-500">Adding to Batch: <span className="font-mono font-bold text-blue-700">{selectedBatch?.batch_number}</span></p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddStepModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddStep} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Step Name *</label>
                <input
                  type="text"
                  required
                  value={newStepForm.name}
                  onChange={(e) => setNewStepForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g. Step 3 — Reaction"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Step Sequence</label>
                  <input
                    type="number"
                    value={newStepForm.step_number}
                    onChange={(e) => setNewStepForm(prev => ({ ...prev, step_number: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Status</label>
                  <select
                    value={newStepForm.status}
                    onChange={(e) => setNewStepForm(prev => ({ ...prev, status: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  >
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="warning">Warning / Excursion</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Notes / Instructions</label>
                <textarea
                  rows="2"
                  value={newStepForm.notes}
                  onChange={(e) => setNewStepForm(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Reaction temperature window 70–75°C"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddStepModal(false)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? "Saving..." : "Add Step"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD IN-PROCESS CHECK (IPC) WITH LIVE AUTO OOL EVALUATION */}
      {showAddIpcModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-2xs">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Record In-Process Check (IPC)</h3>
                <p className="text-xs text-slate-500">
                  Recording for Batch: <span className="font-mono font-bold text-blue-700">{selectedBatch?.batch_number}</span>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddIpcModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddIpc} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Manufacturing Step *</label>
                <select
                  value={newIpcForm.manufacturing_step_id}
                  onChange={(e) => setNewIpcForm(prev => ({ ...prev, manufacturing_step_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                >
                  {(selectedBatch?.manufacturing_steps || []).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                  {(!selectedBatch?.manufacturing_steps || selectedBatch.manufacturing_steps.length === 0) && (
                    <option value="">Step 3 — Reaction (Default)</option>
                  )}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Parameter *</label>
                  <input
                    type="text"
                    required
                    value={newIpcForm.parameter}
                    onChange={(e) => setNewIpcForm(prev => ({ ...prev, parameter: e.target.value }))}
                    placeholder="e.g. Temperature"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Unit of Measurement</label>
                  <input
                    type="text"
                    value={newIpcForm.unit}
                    onChange={(e) => setNewIpcForm(prev => ({ ...prev, unit: e.target.value }))}
                    placeholder="°C, pH, rpm"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Spec Minimum *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={newIpcForm.spec_min}
                    onChange={(e) => setNewIpcForm(prev => ({ ...prev, spec_min: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Spec Maximum *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={newIpcForm.spec_max}
                    onChange={(e) => setNewIpcForm(prev => ({ ...prev, spec_max: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Actual Value *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={newIpcForm.actual_value}
                    onChange={(e) => setNewIpcForm(prev => ({ ...prev, actual_value: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono font-bold text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Dynamic Live Quality Evaluation */}
              <div className={`rounded-xl border p-3 flex items-center justify-between ${
                computedIpcStatus.isOol
                  ? "border-red-300 bg-red-50 text-red-900 ring-1 ring-red-200"
                  : "border-emerald-300 bg-emerald-50 text-emerald-900"
              }`}>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider">Automated Quality Evaluation</span>
                  <div className="font-bold text-xs mt-0.5">
                    {computedIpcStatus.label}
                  </div>
                  <div className="text-[11px] opacity-80">
                    {computedIpcStatus.isOol 
                      ? `Result (${newIpcForm.actual_value}${newIpcForm.unit}) exceeds approved range (${newIpcForm.spec_min}–${newIpcForm.spec_max}${newIpcForm.unit}). Excursion flag will be raised.` 
                      : `Result (${newIpcForm.actual_value}${newIpcForm.unit}) is within approved range (${newIpcForm.spec_min}–${newIpcForm.spec_max}${newIpcForm.unit}).`}
                  </div>
                </div>
                <span className={`text-base font-bold ${computedIpcStatus.isOol ? "text-red-700" : "text-emerald-700"}`}>
                  {computedIpcStatus.isOol ? "⚠️ OUT-OF-LIMIT (OOL)" : "✓ PASS"}
                </span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Operator</label>
                <input
                  type="text"
                  value={newIpcForm.operator}
                  onChange={(e) => setNewIpcForm(prev => ({ ...prev, operator: e.target.value }))}
                  placeholder="Operator K. Sharma"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddIpcModal(false)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? "Recording..." : "Record In-Process Check"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD RAW MATERIAL LOT */}
      {showAddRmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-2xs">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Add Raw Material</h3>
                <p className="text-xs text-slate-500">Charging to Batch: <span className="font-mono font-bold text-blue-700">{selectedBatch?.batch_number}</span></p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddRmModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddRawMaterial} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Material Name *</label>
                <input
                  type="text"
                  required
                  value={newRmForm.name}
                  onChange={(e) => setNewRmForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g. Isobutylbenzene"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Material Code</label>
                  <input
                    type="text"
                    value={newRmForm.material_code}
                    onChange={(e) => setNewRmForm(prev => ({ ...prev, material_code: e.target.value }))}
                    placeholder="RM-IBB-01"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Lot Number *</label>
                  <input
                    type="text"
                    required
                    value={newRmForm.lot_number}
                    onChange={(e) => setNewRmForm(prev => ({ ...prev, lot_number: e.target.value }))}
                    placeholder="RM-2026-055"
                    className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Supplier</label>
                  <input
                    type="text"
                    value={newRmForm.supplier_name}
                    onChange={(e) => setNewRmForm(prev => ({ ...prev, supplier_name: e.target.value }))}
                    placeholder="ChemCorp"
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Status</label>
                  <select
                    value={newRmForm.status}
                    onChange={(e) => setNewRmForm(prev => ({ ...prev, status: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:border-blue-500 focus:outline-none"
                  >
                    <option value="Approved">Approved</option>
                    <option value="Quarantined">Quarantined</option>
                    <option value="Rejected">Rejected</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddRmModal(false)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? "Saving..." : "Add Raw Material"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
