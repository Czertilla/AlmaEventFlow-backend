from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class ProfileServiceUnavailable(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.PROFILE_SERVICE_UNAVAILABLE


class InvitePersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVITE_PERSON_NOT_FOUND