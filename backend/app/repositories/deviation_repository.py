from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.core.enums import DeviationStatus, DeviationType, Severity
from app.models.deviation import Deviation
from app.repositories.base import BaseRepository


class DeviationRepository(BaseRepository[Deviation]):
    model = Deviation

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        company_id: UUID | None = None,
        status: DeviationStatus | None = None,
        severity: Severity | None = None,
        deviation_type: DeviationType | None = None,
    ) -> tuple[list[Deviation], int]:
        stmt = select(Deviation)
        count_stmt = select(func.count()).select_from(Deviation)

        conditions = []
        if company_id is not None:
            conditions.append(Deviation.company_id == company_id)
        if status is not None:
            conditions.append(Deviation.status == status)
        if severity is not None:
            conditions.append(Deviation.severity == severity)
        if deviation_type is not None:
            conditions.append(Deviation.deviation_type == deviation_type)

        for condition in conditions:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        stmt = stmt.order_by(Deviation.created_at.desc()).limit(limit).offset(offset)

        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def next_reference(self) -> str:
        """Generate a sequential, year-scoped reference like DEV-2026-000042."""
        year = datetime.now(timezone.utc).year
        stmt = select(func.count()).select_from(Deviation).where(
            Deviation.reference.like(f"DEV-{year}-%")
        )
        used = int((await self.session.execute(stmt)).scalar_one())
        return f"DEV-{year}-{used + 1:06d}"

    async def _count_by(self, column, company_id: UUID | None = None) -> list[tuple[str, int]]:
        stmt = select(column, func.count())
        if company_id is not None:
            stmt = stmt.where(Deviation.company_id == company_id)
        stmt = stmt.group_by(column)
        rows = (await self.session.execute(stmt)).all()
        result: list[tuple[str, int]] = []
        for key, count in rows:
            if key is None:
                label = "unset"
            elif hasattr(key, "value"):
                label = key.value
            else:
                label = str(key)
            result.append((label, int(count)))
        return result

    async def summary(self, company_id: UUID | None = None) -> dict:
        count_stmt = select(func.count()).select_from(Deviation)
        if company_id is not None:
            count_stmt = count_stmt.where(Deviation.company_id == company_id)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        return {
            "total": total,
            "by_status": await self._count_by(Deviation.status, company_id),
            "by_severity": await self._count_by(Deviation.severity, company_id),
            "by_type": await self._count_by(Deviation.deviation_type, company_id),
        }
