from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class PersonAlreadyHasAccountException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.PERSON_ALREADY_HAS_ACCOUNT


class ProfileAlreadyExistsException(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = ErrorCode.PROFILE_ALREADY_EXISTS


class AccountLinkOutOfSyncException(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.ACCOUNT_LINK_OUT_OF_SYNC
