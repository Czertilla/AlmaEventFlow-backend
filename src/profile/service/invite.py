from profile.dto.invite import InviteTokenCreateDTO, InviteTokenDTO
from profile.exc.account import PersonAlreadyHasAccountException
from profile.exc.invite import InviteSigningNotConfigured
from profile.exc.person import PersonNotExistsException
from profile.uow.person import PersonUOW
from uuid import UUID

from core.config.settings import settings
from core.service.base import BaseService, required_transaction
from core.utils.invite import InviteSigningUnavailableError, encode_invite_token


class InviteService(BaseService[PersonUOW]):
    @required_transaction
    async def _ensure_invitable(self, person_id: UUID) -> None:
        if not await self.uow.persons.exists_id(person_id):
            raise PersonNotExistsException()
        if await self.uow.account_links.get_by_person(person_id) is not None:
            raise PersonAlreadyHasAccountException()

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
