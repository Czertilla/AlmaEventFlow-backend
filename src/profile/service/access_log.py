from collections.abc import Mapping
from profile.access.decision import Via
from profile.dto.access import AccessFieldDTO, AccessLogEntryDTO
from profile.enum.access import AccessAction
from profile.models.access_log import SensitiveAccessLogORM
from profile.models.access_request import AccessRequestORM
from profile.registry import UnknownFieldError, get_field
from profile.uow.access_log import AccessLogUOW
from uuid import UUID

from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService


def _field(key: str) -> AccessFieldDTO:
    try:
        return AccessFieldDTO(key=key, label=get_field(key).label)
    except UnknownFieldError:
        return AccessFieldDTO(key=key, label=key)


def _entry(
    row: SensitiveAccessLogORM,
    subject_id: UUID,
    names: Mapping[UUID, str],
    requests: Mapping[UUID, AccessRequestORM],
) -> AccessLogEntryDTO:
    by_self = row.actor_person_id == subject_id
    request = requests.get(row.request_id) if row.request_id else None
    return AccessLogEntryDTO(
        id=row.id,
        created_at=row.created_at,
        action=AccessAction(row.action),
        outcome=row.outcome,
        fields=[_field(key) for key in row.fields],
        by_self=by_self,
        by_administrator=row.via == Via.SUPERUSER.value,
        actor_person_id=row.actor_person_id,
        actor_name=None
        if by_self or row.actor_person_id is None
        else names.get(row.actor_person_id),
        request_id=row.request_id,
        comment=request.comment if request else None,
        collective_name=request.collective_name if request else None,
    )


class AccessLogService(BaseService[AccessLogUOW]):
    async def of_subject(
        self, person_id: UUID | None, page: PageParamDTO = PageParamDTO()
    ) -> PageDTO[AccessLogEntryDTO]:
        if person_id is None:
            return PageDTO(
                items=[],
                pagination=PaginationDTO(page=page.page, limit=page.limit, total=0),
            )
        async with self.uow as uow:
            rows, total = await uow.access_log.of_subject(person_id, page)
            actors = {
                row.actor_person_id
                for row in rows
                if row.actor_person_id is not None and row.actor_person_id != person_id
            }
            names = {
                person.id: " ".join(
                    part
                    for part in (person.surname, person.name, person.patronymic)
                    if part
                )
                for person in (await uow.persons.by_ids(actors) if actors else [])
            }
            requests = {
                request.id: request
                for request in await uow.access_requests.by_ids(
                    {row.request_id for row in rows if row.request_id}
                )
            }
            items = [_entry(row, person_id, names, requests) for row in rows]
        return PageDTO(
            items=items,
            pagination=PaginationDTO(page=page.page, limit=page.limit, total=total),
        )
