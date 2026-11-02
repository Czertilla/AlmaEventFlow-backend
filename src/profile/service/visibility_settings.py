from datetime import UTC, datetime
from profile.dto.visibility import VisibilityChangeDTO, VisibilityEntryDTO
from profile.enum.audience import Audience, clamp
from profile.exc.person import PersonNotExistsException
from profile.exc.visibility import (
    VisibilityCooldown,
    VisibilityFieldNotFound,
    VisibilityNotConfigurable,
    VisibilityOutOfRange,
)
from profile.registry import (
    UNIT_HEAD_TYPES,
    PersonalField,
    all_fields,
    get_field,
)
from profile.registry.fields import UnknownFieldError
from profile.service.link_cooldown import link_cooldown_left
from profile.uow.visibility import VisibilityUOW
from uuid import UUID

from core.enum.notify import NotificationCategory
from core.service.base import BaseService, required_transaction
from core.utils.tz import localize

OWNER = "owner"
ADMIN = "admin"

WIDENED_TO = {
    Audience.CONTEXT: "участникам ваших коллективов",
    Audience.ALL_USERS: "всем пользователям",
}


def _field(field_key: str) -> PersonalField:
    try:
        field = get_field(field_key)
    except UnknownFieldError:
        raise VisibilityFieldNotFound() from None
    if field.deprecated:
        raise VisibilityFieldNotFound()
    return field


def _entry(
    field: PersonalField, stored: str | None, unit_head: bool
) -> VisibilityEntryDTO:
    default = field.default_for(unit_head=unit_head)
    chosen = Audience(stored) if stored is not None else default
    return VisibilityEntryDTO(
        key=field.key,
        label=field.label,
        configurable=field.configurable,
        audience_min=field.audience_min,
        audience_max=field.audience_max,
        audience_default=default,
        audience=clamp(chosen, field.audience_min, field.audience_max),
        is_default=stored is None,
    )


class VisibilitySettingsService(BaseService[VisibilityUOW]):
    @required_transaction
    async def _is_unit_head(self, person_id: UUID) -> bool:
        heads = await self.uow.organizations.principals(UNIT_HEAD_TYPES, [person_id])
        return person_id in heads

    @required_transaction
    async def _ensure_person(self, person_id: UUID) -> None:
        if not await self.uow.persons.exists_id(person_id):
            raise PersonNotExistsException()

    @required_transaction
    async def _entries(self, person_id: UUID | None) -> list[VisibilityEntryDTO]:
        shown = [field for field in all_fields() if not field.deprecated]
        if person_id is None:
            return [_entry(field, None, False) for field in shown]
        stored = await self.uow.visibility.of_person(person_id)
        unit_head = await self._is_unit_head(person_id)
        return [_entry(field, stored.get(field.key), unit_head) for field in shown]

    @required_transaction
    async def _check_cooldown(self, person_id: UUID, now: datetime) -> None:
        left = await link_cooldown_left(self.uow.account_history, person_id, now)
        if left is not None:
            seconds = int(left.total_seconds()) + 1
            raise VisibilityCooldown(headers={"Retry-After": str(seconds)})

    @required_transaction
    async def _apply(
        self,
        person_id: UUID,
        field: PersonalField,
        requested: Audience | None,
        *,
        actor_user_id: UUID,
        source: str,
    ) -> VisibilityEntryDTO:
        await self._ensure_person(person_id)
        now = datetime.now(UTC)
        stored = (await self.uow.visibility.of_person(person_id)).get(field.key)
        unit_head = await self._is_unit_head(person_id)
        default = field.default_for(unit_head=unit_head)
        current = _entry(field, stored, unit_head).audience
        target = default if requested is None else requested
        if target == current:
            return _entry(field, stored, unit_head)
        widened = target.rank > current.rank
        if widened and source == OWNER:
            await self._check_cooldown(person_id, now)
        if target == default:
            await self.uow.visibility.clear(person_id, field.key)
            kept = None
        else:
            await self.uow.visibility.put(person_id, field.key, target.value)
            kept = target.value
        await self.uow.visibility_history.record(
            person_id,
            field.key,
            old_audience=stored,
            new_audience=kept,
            actor_user_id=actor_user_id,
            source=source,
        )
        if widened:
            local = localize(now)
            await self.uow.notification_outbox.enqueue(
                person_id=person_id,
                category=NotificationCategory.system.value,
                title="Видимость данных расширена",
                body=(
                    f"Поле «{field.label}» теперь видно {WIDENED_TO[target]}. "
                    f"{local:%d.%m.%Y %H:%M} {local.tzname()}."
                ),
                data={
                    "kind": "visibility_widened",
                    "field": field.key,
                    "audience": target.value,
                },
                now=now,
            )
        return _entry(field, kept, unit_head)

    async def entries(self, person_id: UUID | None) -> list[VisibilityEntryDTO]:
        async with self.uow:
            return await self._entries(person_id)

    async def set(
        self,
        person_id: UUID,
        field_key: str,
        change: VisibilityChangeDTO,
        *,
        actor_user_id: UUID,
        source: str,
    ) -> VisibilityEntryDTO:
        field = _field(field_key)
        self._ensure_settable(field)
        audience = change.audience
        if not field.audience_min.rank <= audience.rank <= field.audience_max.rank:
            raise VisibilityOutOfRange()
        async with self.uow as uow:
            entry = await self._apply(
                person_id,
                field,
                audience,
                actor_user_id=actor_user_id,
                source=source,
            )
            await uow.commit()
        return entry

    async def reset(
        self, person_id: UUID, field_key: str, *, actor_user_id: UUID, source: str
    ) -> VisibilityEntryDTO:
        field = _field(field_key)
        self._ensure_settable(field)
        async with self.uow as uow:
            entry = await self._apply(
                person_id, field, None, actor_user_id=actor_user_id, source=source
            )
            await uow.commit()
        return entry

    @staticmethod
    def _ensure_settable(field: PersonalField) -> None:
        if not field.configurable:
            raise VisibilityNotConfigurable()
