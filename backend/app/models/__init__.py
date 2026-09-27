"""ORM models package.

Importing the models here ensures they are registered on the shared
``Base.metadata`` (used by Alembic autogenerate and by the test harness that
creates tables)."""

from app.db.base import Base
from app.models.audit import AuditEvent
from app.models.deviation import Deviation
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.org import Company, CompanyMembership, Profile, Site

__all__ = [
    "Base",
    "Deviation",
    "AuditEvent",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "Company",
    "Site",
    "Profile",
    "CompanyMembership",
]
