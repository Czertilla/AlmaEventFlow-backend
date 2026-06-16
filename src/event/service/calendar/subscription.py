import datetime
from uuid import UUID

from fastapi import status

from core.schema.error import ErrorCode
from core.schema.user import UserJWT
from core.service.base import BaseService, required_transaction
from core.utils.exc.http import VancedHTTPException
from event.enum.calendar import CalendarSubscriptionTypeEnum
from event.exc.event import CollectiveNotExistsException
from event.models.calendar import CalendarSubscriptionORM
from event.schema.calendar import (
    AvailableFeeds,
    FeedDescriptor,
    SubscriptionCreate,
)
from event.uow.calendar import CalendarUOW
from .token import CalendarTokenService

PERSONAL_FALLBACK = "Мои мероприятия"


def _personal_title(full_name: str) -> str:
    return f"{full_name} — AlmaEventFlow"


def _member_title(name: str) -> str:
    return f"{name} — AlmaEventFlow"


def _principal_title(name: str) -> str:
    return f"{name} (руководитель) — AlmaEventFlow"


class CalendarSubscriptionService(BaseService[CalendarUOW]):
    def __init__(self, uow: CalendarUOW) -> None:
        super().__init__(uow)
        self._tokens = CalendarTokenService()

    @required_transaction
    async def _insert(self, data: dict) -> CalendarSubscriptionORM:
        sub = await self.uow.calendar_subscriptions.add_n_return(data=data)
        return await self.uow.calendar_subscriptions.get_loaded(sub.id)

    @required_transaction
    async def _get_owned(
        self, owner_user_id: UUID, subscription_id: UUID
    ) -> CalendarSubscriptionORM:
        sub = await self.uow.calendar_subscriptions.get_loaded(subscription_id)
        if sub is None or sub.owner_user_id != owner_user_id:
            raise VancedHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorCode.CALENDAR_SUBSCRIPTION_NOT_FOUND,
            )
        return sub

    async def _resolve_title(
        self,
        type_: CalendarSubscriptionTypeEnum,
        collective_id: UUID | None,
        person_id: UUID | None,
    ) -> str:
        if type_ == CalendarSubscriptionTypeEnum.personal_all:
            full_name = await self.uow.calendar_feed.person_full_name(
                person_id
            )
            return _personal_title(full_name or PERSONAL_FALLBACK)
        collective = await self.uow.collectives.get_by_id(collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        if type_ == CalendarSubscriptionTypeEnum.principal_collective:
            return _principal_title(collective.name)
        return _member_title(collective.name)

    async def _authorize(
        self, user: UserJWT, data: SubscriptionCreate
    ) -> None:
        if user.person_id is None:
            raise VancedHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorCode.ATTACHED_PERSON_REQUIRED,
            )
        if data.type == CalendarSubscriptionTypeEnum.personal_all:
            return
        if data.type == CalendarSubscriptionTypeEnum.personal_collective:
            is_member = await self.uow.calendar_feed.member_exists(
                user.person_id, data.collective_id
            )
            if not is_member and not user.is_superuser:
                raise VancedHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorCode.NOT_MEMBER_PERSON,
                )
            return
        collective = await self.uow.collectives.get_by_id(data.collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        if (
            not user.is_superuser
            and collective.principal_id != user.person_id
        ):
            raise VancedHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorCode.NOT_COLLECTIVE_PRINCIPAL,
            )

    async def available_feeds(self, user: UserJWT) -> AvailableFeeds:
        async with self.uow:
            if user.person_id is None:
                return AvailableFeeds()
            full_name = await self.uow.calendar_feed.person_full_name(
                user.person_id
            )
            member_collectives = (
                await self.uow.calendar_feed.member_collectives(user.person_id)
            )
            principal_collectives = (
                await self.uow.collectives.get_by_principal_id(user.person_id)
            )
            return AvailableFeeds(
                personal=FeedDescriptor(
                    type=CalendarSubscriptionTypeEnum.personal_all,
                    title=_personal_title(full_name or PERSONAL_FALLBACK),
                ),
                member_collectives=[
                    FeedDescriptor(
                        type=CalendarSubscriptionTypeEnum.personal_collective,
                        title=_member_title(c.name),
                        collective_id=c.id,
                    )
                    for c in member_collectives
                ],
                principal_collectives=[
                    FeedDescriptor(
                        type=CalendarSubscriptionTypeEnum.principal_collective,
                        title=_principal_title(c.name),
                        collective_id=c.id,
                    )
                    for c in principal_collectives
                ],
            )

    async def list_active(
        self, user: UserJWT
    ) -> list[CalendarSubscriptionORM]:
        async with self.uow:
            return await self.uow.calendar_subscriptions.get_active_by_owner(
                user.id
            )

    async def create(
        self, user: UserJWT, data: SubscriptionCreate
    ) -> tuple[CalendarSubscriptionORM, str]:
        async with self.uow as uow:
            await self._authorize(user, data)
            title = await self._resolve_title(
                data.type, data.collective_id, user.person_id
            )
            token = self._tokens.generate()
            type_id = await self.uow.calendar_subscriptions.resolve_type_id(
                data.type.value
            )
            sub = await self._insert(
                {
                    "owner_user_id": user.id,
                    "person_id": user.person_id,
                    "collective_id": data.collective_id,
                    "type_id": type_id,
                    "title": title,
                    "token_hash": self._tokens.hash(token),
                }
            )
            await uow.commit()
        return sub, token

    async def rotate_token(
        self, user: UserJWT, subscription_id: UUID
    ) -> tuple[CalendarSubscriptionORM, str]:
        async with self.uow as uow:
            await self._get_owned(user.id, subscription_id)
            token = self._tokens.generate()
            await self.uow.calendar_subscriptions.update_one(
                subscription_id,
                {
                    "token_hash": self._tokens.hash(token),
                    "is_active": True,
                    "revoked_at": None,
                },
            )
            sub = await self.uow.calendar_subscriptions.get_loaded(
                subscription_id
            )
            await uow.commit()
        return sub, token

    async def delete(self, user: UserJWT, subscription_id: UUID) -> None:
        async with self.uow as uow:
            await self._get_owned(user.id, subscription_id)
            await self.uow.calendar_subscriptions.update_one(
                subscription_id,
                {
                    "is_active": False,
                    "revoked_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ),
                },
            )
            await uow.commit()
