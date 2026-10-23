from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from event.dto.feed import RosterMemberDTO, ViewerCollectiveDTO, ViewerContextDTO
from event.dto.member_profile import MemberPersonDTO, ProfileViewerDTO
from event.repository.view import ViewRepo


async def viewer_context(view: ViewRepo, viewer: ProfileViewerDTO) -> ViewerContextDTO:
    rows: Sequence[Row[Any]] = (
        await view.collectives_of(viewer.person_id) if viewer.person_id else []
    )
    roles = await view.roles_of_members(
        [row.member_id for row in rows if row.member_id]
    )
    return ViewerContextDTO(
        person_id=viewer.person_id,
        is_superuser=viewer.is_superuser,
        collectives=[
            ViewerCollectiveDTO(
                id=row.id,
                name=row.name,
                is_verified=row.is_verified,
                is_principal=row.principal_id == viewer.person_id,
                member_id=row.member_id,
                member_is_active=row.member_is_active,
                roles=roles.get(row.member_id, []),
            )
            for row in rows
        ],
    )


async def roster_of(
    view: ViewRepo, rows: Sequence[Row[Any]]
) -> dict[UUID, RosterMemberDTO]:
    """The members the rows name, with their roles, by member id."""
    roles = await view.roles_of_members([row.id for row in rows])
    return {
        row.id: RosterMemberDTO(
            id=row.id,
            person=MemberPersonDTO(
                id=row.person_id,
                surname=row.surname,
                name=row.name,
                patronymic=row.patronymic,
            ),
            is_active=row.is_active,
            roles=roles.get(row.id, []),
        )
        for row in rows
    }


async def roster_by_collective(
    view: ViewRepo, collective_ids: Collection[UUID]
) -> dict[UUID, list[RosterMemberDTO]]:
    rows = await view.roster(collective_ids)
    members = await roster_of(view, rows)
    result: dict[UUID, list[RosterMemberDTO]] = {c: [] for c in collective_ids}
    for row in rows:
        result[row.collective_id].append(members[row.id])
    return result
