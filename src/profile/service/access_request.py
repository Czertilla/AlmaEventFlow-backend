from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from profile.access.decision import Via
from profile.dto.access import AccessFieldDTO, ViewerDTO
from profile.dto.access_request import (
    AccessExportCreateDTO,
    AccessExportDTO,
    AccessRequestCreateDTO,
    AccessRequestDTO,
    CollectiveLeadDTO,
    ExportedSubjectDTO,
    GrantStateDTO,
    SkippedSubjectDTO,
)
from profile.enum.access import AccessAction, GrantState, GrantStatus, SkipReason
from profile.exc.access_request import (
    AccessCommentLength,
    AccessExpiresOutOfRange,
    AccessFieldNotGrantable,
    AccessFieldNotRequested,
    AccessRequestExpired,
    AccessRequestNotFound,
    CollectiveNotVerified,
    EventServiceUnavailable,
    NotCollectivePrincipal,
)
from profile.exc.event import EventUnavailableError
from profile.models.access_request import AccessRequestORM
from profile.registry import UnknownFieldError, get_field, grantable_fields
from profile.service.personal_data import (
    PersonalDataService,
    access_entry,
    labels_of,
)
from profile.uow.access_request import AccessRequestUOW
from profile.utils.event import collective_active_members, collective_principal
from uuid import UUID

from core.config.settings import settings
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from core.utils.tz import localize

NOT_GRANTEE = "NOT_GRANTEE"
REQUEST_EXPIRED = "REQUEST_EXPIRED"
FIELD_NOT_REQUESTED = "FIELD_NOT_REQUESTED"
EVENT_UNAVAILABLE = "EVENT_UNAVAILABLE"
NOT_PRINCIPAL = "NOT_PRINCIPAL"
COLLECTIVE_NOT_VERIFIED = "COLLECTIVE_NOT_VERIFIED"
NOT_MEMBER = "NOT_MEMBER"
GRANT_NOT_ACTIVE = "GRANT_NOT_ACTIVE"


def grant_state(status: str, expires_at: datetime, now: datetime) -> GrantState:
    if status in (GrantStatus.PENDING, GrantStatus.ACTIVE) and expires_at <= now:
        return GrantState.EXPIRED
    return GrantState(status)


def access_fields(keys: Collection[str]) -> list[AccessFieldDTO]:
    fields: list[AccessFieldDTO] = []
    for key in sorted(keys):
        try:
            fields.append(AccessFieldDTO(key=key, label=get_field(key).label))
        except UnknownFieldError:
            fields.append(AccessFieldDTO(key=key, label=key))
    order = {field.key: n for n, field in enumerate(grantable_fields())}
    return sorted(fields, key=lambda item: (order.get(item.key, len(order)), item.key))


def _grantable_keys(keys: Sequence[str]) -> list[str]:
    allowed = {field.key for field in grantable_fields()}
    if not keys or len(set(keys)) != len(keys) or not set(keys) <= allowed:
        raise AccessFieldNotGrantable()
    return [field.key for field in grantable_fields() if field.key in keys]


def _comment(text: str) -> str:
    comment = text.strip()
    if not settings.COMMENT_MIN_LEN <= len(comment) <= settings.COMMENT_MAX_LEN:
        raise AccessCommentLength()
    return comment


def _expiry(expires_at: datetime, now: datetime) -> datetime:
    if expires_at.tzinfo is None:
        raise AccessExpiresOutOfRange()
    if not now < expires_at <= now + timedelta(days=settings.GRANT_MAX_TTL_DAYS):
        raise AccessExpiresOutOfRange()
    return expires_at


def _request_dto(request: AccessRequestORM, now: datetime) -> AccessRequestDTO:
    return AccessRequestDTO(
        id=request.id,
        collective_id=request.collective_id,
        collective_name=request.collective_name,
        fields=access_fields([field.field_key for field in request.fields]),
        comment=request.comment,
        expires_at=request.expires_at,
        created_at=request.created_at,
        is_expired=request.expires_at <= now,
        grants=[
            GrantStateDTO(
                person_id=grant.subject_person_id,
                status=grant_state(grant.status, request.expires_at, now),
            )
            for grant in request.grants
        ],
    )


@dataclass(frozen=True, slots=True)
class _Grant:
    id: UUID
    subject: UUID
    status: str


@dataclass(frozen=True, slots=True)
class _Request:
    id: UUID
    grantee: UUID
    collective_id: UUID
    collective_name: str
    comment: str
    expires_at: datetime
    keys: frozenset[str]
    grants: tuple[_Grant, ...]

    @classmethod
    def of(cls, request: AccessRequestORM) -> "_Request":
        return cls(
            id=request.id,
            grantee=request.grantee_person_id,
            collective_id=request.collective_id,
            collective_name=request.collective_name,
            comment=request.comment,
            expires_at=request.expires_at,
            keys=frozenset(field.field_key for field in request.fields),
            grants=tuple(
                _Grant(grant.id, grant.subject_person_id, grant.status)
                for grant in request.grants
            ),
        )


class AccessRequestService(BaseService[AccessRequestUOW]):
    """A collective's leader asks the active members for some of their fields with
    a comment that says why; each member answers through their grant, and the
    leader exports what the active grants open. Every step is journaled."""

    @property
    def _personal_data(self) -> PersonalDataService:
        return PersonalDataService(self.uow)

    @staticmethod
    def fields() -> list[AccessFieldDTO]:
        return [
            AccessFieldDTO(key=field.key, label=field.label)
            for field in grantable_fields()
        ]

    async def create(
        self, data: AccessRequestCreateDTO, viewer: ViewerDTO
    ) -> AccessRequestDTO:
        now = datetime.now(UTC)
        keys = _grantable_keys(data.fields)
        comment = _comment(data.comment)
        expires_at = _expiry(data.expires_at, now)
        lead = await self._lead(viewer, data.collective_id)
        try:
            members = await collective_active_members(data.collective_id)
        except EventUnavailableError:
            raise EventServiceUnavailable() from None
        assert viewer.person_id is not None
        async with self.uow:
            known = {
                person.id
                for person in await self.uow.persons.by_ids(
                    members - {viewer.person_id}
                )
            }
            request = await self.uow.access_requests.create(
                {
                    "grantee_person_id": viewer.person_id,
                    "collective_id": data.collective_id,
                    "collective_name": lead.name or "",
                    "comment": comment,
                    "expires_at": expires_at,
                    "created_by_user_id": viewer.user_id,
                },
                keys,
                sorted(known),
            )
            await self._announce(request, viewer, now)
            dto = _request_dto(request, now)
            await self.uow.commit()
        return dto

    async def mine(
        self,
        viewer: ViewerDTO,
        collective_id: UUID | None = None,
        page: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[AccessRequestDTO]:
        now = datetime.now(UTC)
        if viewer.person_id is None:
            return PageDTO(
                items=[],
                pagination=PaginationDTO(page=page.page, limit=page.limit, total=0),
            )
        async with self.uow:
            rows, total = await self.uow.access_requests.of_grantee(
                viewer.person_id, collective_id, page
            )
            items = [_request_dto(row, now) for row in rows]
        return PageDTO(
            items=items,
            pagination=PaginationDTO(page=page.page, limit=page.limit, total=total),
        )

    async def read(self, request_id: UUID, viewer: ViewerDTO) -> AccessRequestDTO:
        now = datetime.now(UTC)
        async with self.uow:
            request = await self.uow.access_requests.read(request_id)
            if request is None or request.grantee_person_id != viewer.person_id:
                raise AccessRequestNotFound()
            return _request_dto(request, now)

    async def export(
        self, request_id: UUID, data: AccessExportCreateDTO, viewer: ViewerDTO
    ) -> AccessExportDTO:
        now = datetime.now(UTC)
        async with self.uow:
            found = await self.uow.access_requests.read(request_id)
            request = _Request.of(found) if found is not None else None
        if request is None:
            raise AccessRequestNotFound()
        keys = set(request.keys) if data.fields is None else set(data.fields)
        if request.grantee != viewer.person_id:
            await self._refuse(viewer, request, keys, NOT_GRANTEE)
            raise AccessRequestNotFound()
        if request.expires_at <= now:
            await self._refuse(viewer, request, keys, REQUEST_EXPIRED)
            raise AccessRequestExpired()
        if not keys or not keys <= request.keys:
            await self._refuse(viewer, request, keys, FIELD_NOT_REQUESTED)
            raise AccessFieldNotRequested()
        members = await self._current_members(viewer, request, keys)
        exported, skipped, gone = self._split(request, members, now)
        await self._personal_data.deny_many(
            [
                access_entry(
                    viewer,
                    grant.subject,
                    AccessAction.DENIED,
                    keys,
                    NOT_MEMBER,
                    request_id=request.id,
                    grant_id=grant.id,
                )
                for grant in gone
            ]
        )
        async with self.uow:
            still = await self._still_active(request, exported)
            skipped.extend(
                SkippedSubjectDTO(person_id=grant.subject, status=SkipReason.REVOKED)
                for grant in exported
                if grant.id not in still
            )
            exported = [grant for grant in exported if grant.id in still]
            records = await self._personal_data._read_fields(  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
                [grant.subject for grant in exported], keys
            )
            await self._journal_export(viewer, request, exported, keys, now)
            await self.uow.commit()
        return AccessExportDTO(
            request_id=request.id,
            exported_at=now,
            fields=access_fields(keys),
            subjects=[
                ExportedSubjectDTO(
                    person_id=grant.subject, records=records[grant.subject]
                )
                for grant in exported
            ],
            skipped=sorted(skipped, key=lambda item: str(item.person_id)),
        )

    async def _lead(self, viewer: ViewerDTO, collective_id: UUID) -> CollectiveLeadDTO:
        if viewer.person_id is None:
            raise NotCollectivePrincipal()
        try:
            lead = await collective_principal(viewer.person_id, collective_id)
        except EventUnavailableError:
            raise EventServiceUnavailable() from None
        if not lead.is_principal:
            raise NotCollectivePrincipal()
        if not lead.is_verified:
            raise CollectiveNotVerified()
        return lead

    async def _current_members(
        self, viewer: ViewerDTO, request: "_Request", keys: Collection[str]
    ) -> set[UUID]:
        try:
            await self._lead(viewer, request.collective_id)
            return await collective_active_members(request.collective_id)
        except EventServiceUnavailable:
            await self._refuse(viewer, request, keys, EVENT_UNAVAILABLE)
            raise
        except EventUnavailableError:
            await self._refuse(viewer, request, keys, EVENT_UNAVAILABLE)
            raise EventServiceUnavailable() from None
        except NotCollectivePrincipal:
            await self._refuse(viewer, request, keys, NOT_PRINCIPAL)
            raise
        except CollectiveNotVerified:
            await self._refuse(viewer, request, keys, COLLECTIVE_NOT_VERIFIED)
            raise

    @staticmethod
    def _split(
        request: "_Request", members: Collection[UUID], now: datetime
    ) -> tuple[list[_Grant], list[SkippedSubjectDTO], list[_Grant]]:
        exported: list[_Grant] = []
        skipped: list[SkippedSubjectDTO] = []
        gone: list[_Grant] = []
        for grant in request.grants:
            state = grant_state(grant.status, request.expires_at, now)
            if state != GrantState.ACTIVE:
                skipped.append(
                    SkippedSubjectDTO(
                        person_id=grant.subject, status=SkipReason(state.value)
                    )
                )
            elif grant.subject not in members:
                skipped.append(
                    SkippedSubjectDTO(
                        person_id=grant.subject, status=SkipReason.NOT_MEMBER
                    )
                )
                gone.append(grant)
            else:
                exported.append(grant)
        return exported, skipped, gone

    @required_transaction
    async def _still_active(
        self, request: "_Request", grants: Sequence[_Grant]
    ) -> set[UUID]:
        return await self.uow.access_grants.active_among(
            request.id, [grant.id for grant in grants]
        )

    async def _refuse(
        self,
        viewer: ViewerDTO,
        request: "_Request",
        keys: Collection[str],
        reason: str,
    ) -> None:
        await self._personal_data.deny_many(
            [
                access_entry(
                    viewer,
                    None,
                    AccessAction.DENIED,
                    keys,
                    reason,
                    request_id=request.id,
                )
            ]
        )

    @required_transaction
    async def _announce(
        self, request: AccessRequestORM, viewer: ViewerDTO, now: datetime
    ) -> None:
        keys = [field.field_key for field in request.fields]
        await self._personal_data._record(  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
            [
                access_entry(
                    viewer,
                    grant.subject_person_id,
                    AccessAction.REQUEST_CREATED,
                    keys,
                    via=Via.NONE,
                    request_id=request.id,
                    grant_id=grant.id,
                    notified=True,
                )
                for grant in request.grants
            ]
        )
        who = await self._personal_data._actor_name(viewer)  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
        until = localize(request.expires_at)
        body = (
            f"{who}, руководитель коллектива {request.collective_name}, "
            f"просит доступ к вашим данным: {labels_of(keys)}. "
            f"Комментарий: «{request.comment}». "
            f"Запрос действует до {until:%d.%m.%Y %H:%M} {until.tzname()}."
        )
        await self._personal_data._tell_many(  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
            [
                (
                    grant.subject_person_id,
                    "Запрос доступа к вашим данным",
                    body,
                    _notice_data("access_request", request.id, grant.id),
                )
                for grant in request.grants
            ],
            now,
        )

    @required_transaction
    async def _journal_export(
        self,
        viewer: ViewerDTO,
        request: "_Request",
        exported: Sequence[_Grant],
        keys: Collection[str],
        now: datetime,
    ) -> None:
        await self._personal_data._record(  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
            [
                access_entry(
                    viewer,
                    None,
                    AccessAction.EXPORT,
                    keys,
                    via=Via.GRANT,
                    request_id=request.id,
                ),
                *(
                    access_entry(
                        viewer,
                        grant.subject,
                        AccessAction.EXPORT,
                        keys,
                        via=Via.GRANT,
                        request_id=request.id,
                        grant_id=grant.id,
                        notified=True,
                    )
                    for grant in exported
                ),
            ]
        )
        who = await self._personal_data._actor_name(viewer)  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
        local = localize(now)
        body = (
            f"Выгружены ваши данные: {labels_of(keys)}. "
            f"Кто: {who}, коллектив {request.collective_name}. "
            f"Комментарий: «{request.comment}». "
            f"Когда: {local:%d.%m.%Y %H:%M} {local.tzname()}."
        )
        await self._personal_data._tell_many(  # pyright: ignore[reportPrivateUsage]  # composed in this transaction
            [
                (
                    grant.subject,
                    "Выгрузка ваших данных",
                    body,
                    _notice_data("access_export", request.id, grant.id),
                )
                for grant in exported
            ],
            now,
        )


def _notice_data(kind: str, request_id: UUID, grant_id: UUID) -> dict[str, str]:
    return {"kind": kind, "request_id": str(request_id), "grant_id": str(grant_id)}
