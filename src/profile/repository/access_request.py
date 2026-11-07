from collections.abc import Collection, Sequence
from datetime import datetime
from profile.enum.access import GrantStatus
from profile.models.access_request import (
    AccessGrantORM,
    AccessRequestFieldORM,
    AccessRequestORM,
)
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.dto.pagination import PageParams

_REQUEST = (
    selectinload(AccessRequestORM.fields),
    selectinload(AccessRequestORM.grants),
)


class AccessRequestRepo(SQLAlchemyRepository[AccessRequestORM]):
    model = AccessRequestORM

    async def create(
        self,
        values: dict[str, Any],
        field_keys: Sequence[str],
        subjects: Sequence[UUID],
    ) -> AccessRequestORM:
        request = await self.add_entity(
            AccessRequestORM(
                **values,
                fields=[AccessRequestFieldORM(field_key=key) for key in field_keys],
                grants=[
                    AccessGrantORM(
                        subject_person_id=subject, status=GrantStatus.PENDING.value
                    )
                    for subject in subjects
                ],
            )
        )
        found = await self.read(request.id)
        assert found is not None
        return found

    async def read(self, request_id: UUID) -> AccessRequestORM | None:
        stmt = (
            select(AccessRequestORM)
            .options(*_REQUEST)
            .where(AccessRequestORM.id == request_id)
            .execution_options(populate_existing=True)
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def of_grantee(
        self, grantee_person_id: UUID, collective_id: UUID | None, page: PageParams
    ) -> tuple[list[AccessRequestORM], int]:
        where = [AccessRequestORM.grantee_person_id == grantee_person_id]
        if collective_id is not None:
            where.append(AccessRequestORM.collective_id == collective_id)
        total = (
            await self.execute(
                select(func.count()).select_from(AccessRequestORM).where(*where)
            )
        ).scalar_one()
        rows = (
            await self.execute(
                select(AccessRequestORM)
                .options(*_REQUEST)
                .where(*where)
                .order_by(AccessRequestORM.created_at.desc(), AccessRequestORM.id)
                .offset(page.offset)
                .limit(page.limit)
            )
        ).scalars()
        return list(rows), total

    async def by_ids(self, request_ids: Collection[UUID]) -> list[AccessRequestORM]:
        if not request_ids:
            return []
        stmt = select(AccessRequestORM).where(
            AccessRequestORM.id.in_(list(request_ids))
        )
        return list((await self.execute(stmt)).scalars().all())


class AccessGrantRepo(SQLAlchemyRepository[AccessGrantORM]):
    model = AccessGrantORM

    async def lock(self, grant_id: UUID) -> AccessGrantORM | None:
        stmt = (
            select(AccessGrantORM)
            .options(
                selectinload(AccessGrantORM.request).selectinload(
                    AccessRequestORM.fields
                )
            )
            .where(AccessGrantORM.id == grant_id)
            .with_for_update(of=AccessGrantORM)
            .execution_options(populate_existing=True)
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def active_among(
        self, request_id: UUID, grant_ids: Collection[UUID]
    ) -> set[UUID]:
        """The grants still active, held against a revocation until the end of the
        transaction."""
        if not grant_ids:
            return set()
        stmt = (
            select(AccessGrantORM.id)
            .where(
                AccessGrantORM.request_id == request_id,
                AccessGrantORM.id.in_(list(grant_ids)),
                AccessGrantORM.status == GrantStatus.ACTIVE.value,
            )
            .with_for_update(read=True)
        )
        return set((await self.execute(stmt)).scalars().all())

    async def decide(
        self,
        grant: AccessGrantORM,
        status: GrantStatus,
        at: datetime,
        *,
        revoked: bool = False,
    ) -> AccessGrantORM:
        grant.status = status.value
        if revoked:
            grant.revoked_at = at
        else:
            grant.decided_at = at
        await self.flush()
        return grant

    async def incoming(
        self, subject_id: UUID, page: PageParams
    ) -> tuple[list[AccessGrantORM], int]:
        where = AccessGrantORM.subject_person_id == subject_id
        total = (
            await self.execute(
                select(func.count()).select_from(AccessGrantORM).where(where)
            )
        ).scalar_one()
        rows = (
            await self.execute(
                select(AccessGrantORM)
                .options(
                    selectinload(AccessGrantORM.request).selectinload(
                        AccessRequestORM.fields
                    )
                )
                .where(where)
                .order_by(AccessGrantORM.created_at.desc(), AccessGrantORM.id)
                .offset(page.offset)
                .limit(page.limit)
            )
        ).scalars()
        return list(rows), total
