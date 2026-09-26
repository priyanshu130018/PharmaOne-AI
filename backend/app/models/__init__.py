"""ORM models package.

Importing the models here ensures they are registered on the shared
``Base.metadata`` (used by Alembic autogenerate and by the test harness that
creates tables)."""

from app.db.base import Base
from app.models.audit import AuditEvent
from app.models.deviation import Deviation
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

__all__ = ["Base", "Deviation", "AuditEvent", "KnowledgeDocument", "KnowledgeChunk"]
