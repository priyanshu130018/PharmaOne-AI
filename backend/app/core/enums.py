"""Domain vocabulary shared by ORM models and API schemas.

Kept in `core` (a leaf module with no model/schema dependencies) so both the
persistence layer and the contract layer can import it without creating a
circular dependency.
"""

from enum import Enum


class DeviationType(str, Enum):
    PROCESS = "process"
    EQUIPMENT = "equipment"
    DOCUMENTATION = "documentation"
    MATERIAL = "material"
    ENVIRONMENTAL = "environmental"
    PERSONNEL = "personnel"
    LABORATORY = "laboratory"
    UTILITY = "utility"
    OTHER = "other"


class Severity(str, Enum):
    """Provisional deviation classification (GMP-style).

    NOTE: these levels are *configurable/demo* criteria for this module, not a
    universal regulatory severity lookup (see AIVOA Workflow spec, Risk Strategy).
    """

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class Impact(str, Enum):
    """Recommended impact area from AI/risk assessment (demo criteria)."""

    NONE = "none"
    PRODUCT_QUALITY = "product_quality"
    PATIENT_SAFETY = "patient_safety"
    DATA_INTEGRITY = "data_integrity"
    COMPLIANCE = "compliance"
    SUPPLY = "supply"


class DeviationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    CLOSED = "closed"


class BatchStatus(str, Enum):
    NOT_AFFECTED = "not_affected"
    ON_HOLD = "on_hold"
    QUARANTINED = "quarantined"
    RELEASED = "released"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class DeviationSource(str, Enum):
    """How the deviation content entered the system."""

    MANUAL = "manual"
    TEXT = "text"
    EMAIL = "email"
    PDF = "pdf"
    MANUFACTURING = "manufacturing"


class AuditAction(str, Enum):
    """Auditable actions (GMP / 21 CFR Part 11)."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS_DENIED = "ACCESS_DENIED"
    USER_CREATED = "USER_CREATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    DEVIATION_CREATED = "DEVIATION_CREATED"
    DEVIATION_UPDATED = "DEVIATION_UPDATED"
    DEVIATION_PROCESSED = "DEVIATION_PROCESSED"
    AI_RECOMMENDATION_ACCEPTED = "AI_RECOMMENDATION_ACCEPTED"
    AI_RECOMMENDATION_EDITED = "AI_RECOMMENDATION_EDITED"
    INVESTIGATION_CREATED = "INVESTIGATION_CREATED"
    INVESTIGATION_UPDATED = "INVESTIGATION_UPDATED"
    INVESTIGATION_TASK_COMPLETED = "INVESTIGATION_TASK_COMPLETED"
    INVESTIGATION_EVIDENCE_ADDED = "INVESTIGATION_EVIDENCE_ADDED"
    INVESTIGATION_COMPLETED = "INVESTIGATION_COMPLETED"
    ROOT_CAUSE_GENERATED = "ROOT_CAUSE_GENERATED"
    ROOT_CAUSE_CONFIRMED = "ROOT_CAUSE_CONFIRMED"
    CAPA_CREATED = "CAPA_CREATED"
    CAPA_ACTION_UPDATED = "CAPA_ACTION_UPDATED"
    EFFECTIVENESS_RECORDED = "EFFECTIVENESS_RECORDED"
    DEVIATION_CLOSED = "DEVIATION_CLOSED"
    BATCH_RELEASE_DECIDED = "BATCH_RELEASE_DECIDED"
    BATCH_CREATED = "BATCH_CREATED"
    RAW_MATERIAL_CREATED = "RAW_MATERIAL_CREATED"
    RAW_MATERIAL_ADDED = "RAW_MATERIAL_ADDED"
    MANUFACTURING_STEP_RECORDED = "MANUFACTURING_STEP_RECORDED"
    IPC_RECORDED = "IPC_RECORDED"
    OOL_DETECTED = "OOL_DETECTED"
    SEVERITY_CONFIRMED = "SEVERITY_CONFIRMED"
    RCA_CONFIRMED = "RCA_CONFIRMED"
    CAPA_COMPLETED = "CAPA_COMPLETED"
