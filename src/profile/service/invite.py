from profile.dto.invite import InvitePreviewDTO, InviteTokenCreateDTO, InviteTokenDTO
from profile.exc.account import PersonAlreadyHasAccountException
from profile.exc.invite import (
    InvitePersonNotExistsException,
    InviteSigningNotConfigured,
    InviteTokenExpiredException,
    InviteTokenInvalidException,
)
from profile.exc.person import PersonNotExistsException
from profile.uow.person import PersonUOW
from uuid import UUID

import jwt

from core.config.settings import settings
from core.service.base import BaseService, required_transaction
from core.utils.invite import (
    InviteSigningUnavailableError,
    decode_invite_token,
    encode_invite_token,
)


class InviteService(BaseService[PersonUOW]):
    @required_transaction
    async def _ensure_invitable(self, person_id: UUID) -> None:
        if not await self.uow.persons.exists_id(person_id):
            raise PersonNotExistsException()
        if await self.uow.account_links.get_by_person(person_id) is not None:
            raise PersonAlreadyHasAccountException()

    @required_transaction
    async def _preview(self, person_id: UUID) -> InvitePreviewDTO:
        person = await self.uow.persons.get_by_id(person_id)
        if person is None:
            raise InvitePersonNotExistsException()
        if await self.uow.account_links.get_by_person(person_id) is not None:
            raise PersonAlreadyHasAccountException()
        return InvitePreviewDTO(
            surname=person.surname, name=person.name, patronymic=person.patronymic
        )

    async def create(self, invite: InviteTokenCreateDTO) -> InviteTokenDTO:
        async with self.uow:
            await self._ensure_invitable(invite.person_id)
        try:
            token, expires_at = encode_invite_token(
                invite.person_id, invite.expires_in or settings.INVITE_TOKEN_LIFETIME
            )
        except InviteSigningUnavailableError:
            raise InviteSigningNotConfigured() from None
        return InviteTokenDTO(token=token, expires_at=expires_at)

    async def preview(self, token: str) -> InvitePreviewDTO:
        try:
            person_id = decode_invite_token(token)
        except jwt.ExpiredSignatureError:
            raise InviteTokenExpiredException() from None
        except jwt.InvalidTokenError:
            raise InviteTokenInvalidException() from None
        async with self.uow:
            return await self._preview(person_id)
