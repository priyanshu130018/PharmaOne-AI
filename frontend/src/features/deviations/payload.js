// Turns the editable form state into a clean POST /deviations payload.
// Empty strings become omitted (so optional fields stay null server-side),
// and the AI snapshot is attached for audit if the user applied a suggestion.

const OPTIONAL_TEXT_FIELDS = [
  "site_plant",
  "reported_by",
  "occurred_on",
  "detected_on",
  "department",
  "responsible_team",
  "product_name",
  "product_code",
  "batch_number",
  "manufacturing_stage",
  "equipment",
  "expected_condition",
  "actual_condition",
  "duration",
  "parameter",
  "immediate_action",
  "assessment_reason",
];

const OPTIONAL_ENUM_FIELDS = ["batch_status", "impact", "severity"];

export function buildCreatePayload(form, aiSnapshot) {
  const payload = {
    source: form.source || "manual",
    title: (form.title || "").trim(),
    description: (form.description || "").trim(),
    deviation_type: (form.deviation_type || "").toLowerCase().trim(),
    qa_notified: Boolean(form.qa_notified),
  };

  OPTIONAL_TEXT_FIELDS.forEach((f) => {
    const v = (form[f] ?? "").toString().trim();
    if (v) payload[f] = v;
  });

  // If site_plant is populated and department is not set, use site_plant as department location
  if (form.site_plant && !payload.department) {
    payload.department = form.site_plant.trim();
  }

  OPTIONAL_ENUM_FIELDS.forEach((f) => {
    if (form[f]) payload[f] = form[f];
  });

  if (aiSnapshot) {
    if (aiSnapshot.ai_extraction) payload.ai_extraction = aiSnapshot.ai_extraction;
    if (aiSnapshot.ai_assessment) payload.ai_assessment = aiSnapshot.ai_assessment;
  }

  return payload;
}

// Lightweight client-side validation mirroring the backend schema constraints.
export function validateForm(form) {
  const errors = {};
  if (!form.title || form.title.trim().length < 3) {
    errors.title = "Title must be at least 3 characters.";
  }
  if (!form.description || form.description.trim().length < 10) {
    errors.description = "Description must be at least 10 characters.";
  }
  if (!form.deviation_type) {
    errors.deviation_type = "Select a deviation type.";
  }
  return errors;
}

export function isFormValid(form) {
  return (
    Boolean(form.title && form.title.trim().length >= 3) &&
    Boolean(form.description && form.description.trim().length >= 10) &&
    Boolean(form.deviation_type)
  );
}
