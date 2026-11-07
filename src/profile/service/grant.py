from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from profile.access.decision import Via
from profile.dto.access import ViewerDTO
from profile.dto.access_request import IncomingGrantDTO
from profile.enum.access import AccessAction, GrantState, GrantStatus
from profile.exc.access_request import (
    AccessRequestExpired,
    GrantCooldown,
    GrantNotFound,
    GrantStateConflict,
)
from profile.models.access_request import AccessGrantORM
from profile.models.person import PersonORM
from profile.service.access_request import access_fields, grant_state
from profile.service.link_cooldown import link_cooldown_left
from profile.service.personal_data import PersonalDataService, access_entry
from profile.uow.access_request import AccessRequestUOW
from uuid import UUID

from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction


class Decision(StrEnum):
    APPROVE = "approve"
    DECLINE = "decline"
    REVOKE = "revoke"


_ACTIONS = {
    Decision.APPROVE: (
        GrantStatus.PENDING,
        GrantStatus.ACTIVE,
        AccessAction.GRANT_APPROVED,
    ),
    Decision.DECLINE: (
        GrantStatus.PENDING,
        GrantStatus.DECLINED,
        AccessAction.GRANT_DECLINED,
    ),
    Decision.REVOKE: (
        GrantStatus.ACTIVE,
        GrantStatus.REVOKED,
        AccessAction.GRANT_REVOKED,
    ),
}


def _fullname(person: PersonORM) -> str:
    parts = (person.surname, person.name, person.patronymic)
    return " ".join(part for part in parts if part)


def _incoming(
    grant: AccessGrantORM, names: Mapping[UUID, str], now: datetime
) -> IncomingGrantDTO:
    request = grant.request
    return IncomingGrantDTO(
        id=grant.id,
        status=grant_state(grant.status, request.expires_at, now),
        created_at=grant.created_at,
        decided_at=grant.decided_at,
        revoked_at=grant.revoked_at,
        request_id=request.id,
        grantee_person_id=request.grantee_person_id,
        grantee_name=names.get(request.grantee_person_id),
        collective_id=request.collective_id,
        collective_name=request.collective_name,
        fields=access_fields([field.field_key for field in request.fields]),
        comment=request.comment,
        expires_at=request.expires_at,
    )


class GrantService(BaseService[AccessRequestUOW]):
    """The subject's answer to an access request. Only the person the grant is
    for answers it, through the account linked to them in `profile`."""

    async def incoming(
        self, viewer: ViewerDTO, page: PageParamDTO = PageParamDTO()
    ) -> PageDTO[IncomingGrantDTO]:
        now = datetime.now(UTC)
        if viewer.person_id is None:
            return PageDTO(
                items=[],
                pagination=PaginationDTO(page=page.page, limit=page.limit, total=0),
            )
        async with self.uow:
            grants, total = await self.uow.access_grants.incoming(
                viewer.person_id, page
            )
            names = await self._names(grants)
            items = [_incoming(grant, names, now) for grant in grants]
        return PageDTO(
            items=items,
            pagination=PaginationDTO(page=page.page, limit=page.limit, total=total),
        )

    async def decide(
        self, grant_id: UUID, decision: Decision, viewer: ViewerDTO
    ) -> IncomingGrantDTO:
        now = datetime.now(UTC)
        source, target, action = _ACTIONS[decision]
        async with self.uow:
            grant = await self.uow.access_grants.lock(grant_id)
            if (
                grant is None
                or viewer.person_id is None
                or grant.subject_person_id != viewer.person_id
            ):
                raise GrantNotFound()
            state = grant_state(grant.status, grant.request.expires_at, now)
            if decision == Decision.APPROVE and state == GrantState.EXPIRED:
                raise AccessRequestExpired()
            if grant.status != source:
                raise GrantStateConflict()
            if decision == Decision.APPROVE and await link_cooldown_left(
                self.uow.account_history, viewer.person_id, now
            ):
                raise GrantCooldown()
            await self.uow.access_grants.decide(
                grant, target, now, revoked=decision == Decision.REVOKE
            )
            await PersonalDataService(self.uow)._record(  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
                [
                    access_entry(
                        viewer,
                        viewer.person_id,
                        action,
                        [field.field_key for field in grant.request.fields],
                        via=Via.SELF,
                        request_id=grant.request_id,
                        grant_id=grant.id,
                    )
                ]
            )
            dto = _incoming(grant, await self._names([grant]), now)
            await self.uow.commit()
        return dto

    @required_transaction
    async def _names(self, grants: Sequence[AccessGrantORM]) -> dict[UUID, str]:
        grantees = {grant.request.grantee_person_id for grant in grants}
        return {
            person.id: _fullname(person)
            for person in await self.uow.persons.by_ids(grantees)
        }
