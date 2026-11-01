from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class InviteSigningNotConfigured(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.INVITE_SIGNING_NOT_CONFIGURED


class InviteTokenInvalidException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVITE_TOKEN_INVALID


class InviteTokenExpiredException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVITE_TOKEN_EXPIRED


class InvitePersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.INVITE_PERSON_NOT_FOUND
