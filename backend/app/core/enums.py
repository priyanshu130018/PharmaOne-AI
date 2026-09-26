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


class AuditAction(str, Enum):
    """Auditable actions (subset relevant to the deviation module foundation).

    Auth/admin actions (LOGIN, USER_CREATED, ...) are defined in the spec and
    will be recorded once the auth module lands.
    """

    DEVIATION_CREATED = "DEVIATION_CREATED"
    DEVIATION_UPDATED = "DEVIATION_UPDATED"
    DEVIATION_PROCESSED = "DEVIATION_PROCESSED"
    AI_RECOMMENDATION_ACCEPTED = "AI_RECOMMENDATION_ACCEPTED"
    AI_RECOMMENDATION_EDITED = "AI_RECOMMENDATION_EDITED"
