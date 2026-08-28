from logging import getLogger
from typing import Any
from uuid import UUID

from core.broker.rpc import RpcError, rpc_call
from core.enum.notify import TransportTypeEnum
from core.enum.rpc import EventRPC, NotifyRPC, UserRPC
from core.schema.message.core import Ack
from core.schema.message.event import (
    AttendanceData,
    MyAttendanceRequest,
    MyAttendanceResponse,
    MyCollectivesRequest,
    MyCollectivesResponse,
    PatchMyAttendanceRequest,
)
from core.schema.message.notify import (
    ClientData,
    DeregisterClientRequest,
    GetPreferencesRequest,
    PreferenceItemData,
    PreferencesData,
    RegisterClientRequest,
    SetPreferencesRequest,
)
from core.schema.message.user import (
    LinkTelegramOAuthRequest,
    ResolveUserIdRequest,
    UnlinkTelegramOAuthRequest,
    UserIdResponse,
)

logger = getLogger(__name__)


class AefClientError(Exception):
    """Raised when an RPC call to another AEF service fails unexpectedly."""


async def _resolve_user_id(person_id: UUID) -> UUID:
    try:
        response = await rpc_call(
            UserRPC.RESOLVE_USER_ID,
            ResolveUserIdRequest(person_id=person_id),
            UserIdResponse,
        )
    except RpcError as exc:
        raise AefClientError(
            f"user lookup failed for person {person_id}: {exc}"
        ) from exc
    return response.user_id


async def register_notify_client(person_id: UUID, chat_id: int) -> UUID | None:
    """Registers this Telegram chat as a ``telegram``-transport notify client
    for the linked person. Returns the client id (for later deregistration),
    or ``None`` if the call failed (logged, not raised — link succeeds even
    if notify is briefly unavailable; notifications just won't go out yet)."""
    try:
        user_id = await _resolve_user_id(person_id)
        client = await rpc_call(
            NotifyRPC.REGISTER_CLIENT,
            RegisterClientRequest(
                user_id=user_id,
                transport=TransportTypeEnum.telegram,
                endpoint=str(chat_id),
                payload={"chat_id": str(chat_id)},
            ),
            ClientData,
        )
        return client.id
    except Exception as exc:
        logger.warning(
            "notify client registration failed for person %s: %s",
            person_id,
            exc,
        )
        return None


async def deregister_notify_client(person_id: UUID, client_id: UUID) -> None:
    try:
        user_id = await _resolve_user_id(person_id)
        await rpc_call(
            NotifyRPC.DEREGISTER_CLIENT,
            DeregisterClientRequest(user_id=user_id, client_id=client_id),
            Ack,
        )
    except Exception as exc:
        logger.warning(
            "notify client deregistration failed for person %s: %s",
            person_id,
            exc,
        )


async def get_telegram_notifications_enabled(person_id: UUID) -> bool:
    user_id = await _resolve_user_id(person_id)
    try:
        prefs = await rpc_call(
            NotifyRPC.GET_PREFERENCES,
            GetPreferencesRequest(user_id=user_id),
            PreferencesData,
        )
    except RpcError as exc:
        raise AefClientError(
            f"preferences lookup failed for person {person_id}: {exc}"
        ) from exc
    for pref in prefs.preferences:
        if pref.transport == TransportTypeEnum.telegram:
            return pref.is_enabled
    return False


async def set_telegram_notifications_enabled(
    person_id: UUID, is_enabled: bool
) -> None:
    """Full-replace preference update (notify has no per-transport PATCH), so
    the current list is fetched, the ``telegram`` entry flipped, and the
    whole thing sent back."""
    user_id = await _resolve_user_id(person_id)
    try:
        prefs = await rpc_call(
            NotifyRPC.GET_PREFERENCES,
            GetPreferencesRequest(user_id=user_id),
            PreferencesData,
        )
    except RpcError as exc:
        raise AefClientError(
            f"preferences lookup failed for person {person_id}: {exc}"
        ) from exc
    items = list(prefs.preferences)
    for i, pref in enumerate(items):
        if pref.transport == TransportTypeEnum.telegram:
            items[i] = PreferenceItemData(
                transport=pref.transport, is_enabled=is_enabled
            )
            break
    else:
        items.append(
            PreferenceItemData(
                transport=TransportTypeEnum.telegram, is_enabled=is_enabled
            )
        )
    try:
        await rpc_call(
            NotifyRPC.SET_PREFERENCES,
            SetPreferencesRequest(user_id=user_id, preferences=items),
            PreferencesData,
        )
    except RpcError as exc:
        raise AefClientError(
            f"preferences update failed for person {person_id}: {exc}"
        ) from exc


async def register_oauth_link(
    person_id: UUID, telegram_id: int, username: str | None
) -> bool:
    """Syncs a freshly-established bot deep-link into ``user``-service's own
    ``OAuthAccountORM`` table, so the website's Telegram Login Widget can find
    it later. Best-effort: the deep-link itself already succeeded, so a
    transient failure here just means widget login isn't set up yet."""
    try:
        await rpc_call(
            UserRPC.LINK_TELEGRAM_OAUTH,
            LinkTelegramOAuthRequest(
                person_id=person_id,
                telegram_id=str(telegram_id),
                username=username,
            ),
            Ack,
        )
        return True
    except Exception as exc:
        logger.warning(
            "oauth-link registration failed for person %s: %s",
            person_id,
            exc,
        )
        return False


async def deregister_oauth_link(person_id: UUID) -> bool:
    try:
        await rpc_call(
            UserRPC.UNLINK_TELEGRAM_OAUTH,
            UnlinkTelegramOAuthRequest(person_id=person_id),
            Ack,
        )
        return True
    except Exception as exc:
        logger.warning(
            "oauth-link deregistration failed for person %s: %s",
            person_id,
            exc,
        )
        return False


async def get_my_collectives(person_id: UUID) -> list[dict[str, Any]]:
    """Collectives ``person_id`` is the principal of — the RPC responder
    already scopes to the caller, so every row returned is one this person
    leads."""
    try:
        response = await rpc_call(
            EventRPC.MY_COLLECTIVES,
            MyCollectivesRequest(person_id=person_id),
            MyCollectivesResponse,
        )
    except RpcError as exc:
        raise AefClientError(
            f"collectives lookup failed for person {person_id}: {exc}"
        ) from exc
    return [c.model_dump(mode="json") for c in response.collectives]


async def get_my_attendance(
    person_id: UUID, event_id: UUID
) -> list[dict[str, Any]]:
    try:
        response = await rpc_call(
            EventRPC.MY_ATTENDANCE,
            MyAttendanceRequest(person_id=person_id, event_id=event_id),
            MyAttendanceResponse,
        )
    except RpcError as exc:
        raise AefClientError(
            f"attendance lookup failed for person {person_id}, "
            f"event {event_id}: {exc}"
        ) from exc
    return [a.model_dump(mode="json") for a in response.attendances]


async def patch_my_attendance(
    person_id: UUID,
    member_id: UUID,
    attendance_id: UUID,
    *,
    is_attended: bool,
) -> dict[str, Any]:
    try:
        response = await rpc_call(
            EventRPC.PATCH_MY_ATTENDANCE,
            PatchMyAttendanceRequest(
                person_id=person_id,
                member_id=member_id,
                attendance_id=attendance_id,
                is_attended=is_attended,
            ),
            AttendanceData,
        )
    except RpcError as exc:
        raise AefClientError(
            f"attendance patch failed for person {person_id}, "
            f"attendance {attendance_id}: {exc}"
        ) from exc
    return response.model_dump(mode="json")
