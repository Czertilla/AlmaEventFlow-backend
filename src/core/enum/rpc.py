from enum import StrEnum

from core.utils.enum.prefix import prefix


@prefix("rpc.user.")
class UserRPC(StrEnum):
    RESOLVE_USER_ID = "resolve-user-id"
    LINK_TELEGRAM_OAUTH = "link-telegram-oauth"
    UNLINK_TELEGRAM_OAUTH = "unlink-telegram-oauth"


@prefix("rpc.event.")
class EventRPC(StrEnum):
    MY_COLLECTIVES = "my-collectives"
    MY_ATTENDANCE = "my-attendance"
    PATCH_MY_ATTENDANCE = "patch-my-attendance"


@prefix("rpc.notify.")
class NotifyRPC(StrEnum):
    REGISTER_CLIENT = "register-client"
    DEREGISTER_CLIENT = "deregister-client"
    GET_PREFERENCES = "get-preferences"
    SET_PREFERENCES = "set-preferences"
