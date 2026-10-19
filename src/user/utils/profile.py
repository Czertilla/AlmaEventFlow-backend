from logging import getLogger
from uuid import UUID

from core.broker.rpc import RpcError, rpc_call
from core.enum.rpc import ProfileRPC
from core.schema.error import ErrorCode
from core.schema.message.core import Ack
from core.schema.message.profile import LinkAccountRequest
from core.utils.exc.http import VancedHTTPException
from user.exceptions.profile import (
    InvitePersonNotExistsException,
    ProfileServiceUnavailable,
)
from user.exceptions.user import AccountAlreadyLinked, PersonAlreadyHasAccount

logger = getLogger(__name__)

_REFUSALS: dict[str, type[VancedHTTPException]] = {
    ErrorCode.PERSON_NOT_FOUND: InvitePersonNotExistsException,
    ErrorCode.PERSON_ALREADY_HAS_ACCOUNT: PersonAlreadyHasAccount,
    ErrorCode.ACCOUNT_ALREADY_LINKED: AccountAlreadyLinked,
}


async def link_account(
    user_id: UUID, person_id: UUID, *, replace: bool = False
) -> None:
    request = LinkAccountRequest(user_id=user_id, person_id=person_id, replace=replace)
    try:
        await rpc_call(ProfileRPC.LINK_ACCOUNT, request, Ack)
    except RpcError as exc:
        refusal = _REFUSALS.get(exc.error.detail)
        if refusal is not None:
            raise refusal() from exc
        raise VancedHTTPException(
            status_code=exc.error.code, detail=exc.error.detail
        ) from exc
    except Exception as exc:
        logger.exception("The profile service did not answer a link request")
        raise ProfileServiceUnavailable() from exc
