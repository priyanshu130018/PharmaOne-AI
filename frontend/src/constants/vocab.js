// Controlled vocabularies. These MUST stay in sync with the backend enums in
// `backend/app/core/enums.py`. Values are the wire format; labels are display-only.

const opt = (value, label) => ({ value, label });

export const DEVIATION_TYPES = [
  opt("process", "Process"),
  opt("equipment", "Equipment"),
  opt("documentation", "Documentation"),
  opt("material", "Material"),
  opt("environmental", "Environmental"),
  opt("personnel", "Personnel"),
  opt("laboratory", "Laboratory"),
  opt("utility", "Utility"),
  opt("other", "Other"),
];

export const SEVERITIES = [
  opt("minor", "Minor"),
  opt("major", "Major"),
  opt("critical", "Critical"),
];

export const IMPACTS = [
  opt("none", "None"),
  opt("product_quality", "Product quality"),
  opt("patient_safety", "Patient safety"),
  opt("data_integrity", "Data integrity"),
  opt("compliance", "Compliance"),
  opt("supply", "Supply"),
];

export const BATCH_STATUSES = [
  opt("not_affected", "Not affected"),
  opt("on_hold", "On hold"),
  opt("quarantined", "Quarantined"),
  opt("released", "Released"),
  opt("rejected", "Rejected"),
  opt("unknown", "Unknown"),
];

export const SOURCES = [
  opt("manual", "Manual entry"),
  opt("text", "Pasted text"),
  opt("email", "Email"),
  opt("pdf", "PDF"),
];

// Tailwind classes for severity / impact badges.
export const SEVERITY_STYLES = {
  minor: "bg-emerald-100 text-emerald-700 border-emerald-200",
  major: "bg-amber-100 text-amber-800 border-amber-200",
  critical: "bg-red-100 text-red-700 border-red-200",
};

export const labelFor = (options, value) =>
  options.find((o) => o.value === value)?.label ?? value ?? "—";
