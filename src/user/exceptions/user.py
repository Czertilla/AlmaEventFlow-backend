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
