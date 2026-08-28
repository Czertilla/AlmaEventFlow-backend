from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class UsernameAlreadyExists(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.USERNAME_ALREADY_EXISTS


class InviteTokenInvalid(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVITE_TOKEN_INVALID


class InviteTokenExpired(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVITE_TOKEN_EXPIRED


class PersonAlreadyHasAccount(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.PERSON_ALREADY_HAS_ACCOUNT


class SessionNotFound(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.SESSION_NOT_FOUND


class InvalidCurrentPassword(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVALID_CURRENT_PASSWORD


class TelegramLinkPersonRequired(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.TELEGRAM_LINK_PERSON_REQUIRED


class TelegramBotNotConfigured(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.TELEGRAM_BOT_NOT_CONFIGURED


class TelegramAuthInvalid(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.TELEGRAM_AUTH_INVALID


class TelegramAccountNotLinked(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.TELEGRAM_ACCOUNT_NOT_LINKED


class UserNotFound(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.USER_NOT_FOUND


class AccountAlreadyLinked(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.ACCOUNT_ALREADY_LINKED
