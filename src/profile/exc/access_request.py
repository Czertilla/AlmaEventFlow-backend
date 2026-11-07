from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class AccessRequestNotFound(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.ACCESS_REQUEST_NOT_FOUND


class AccessRequestExpired(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.ACCESS_REQUEST_EXPIRED


class AccessFieldNotGrantable(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.ACCESS_FIELD_NOT_GRANTABLE


class AccessFieldNotRequested(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.ACCESS_FIELD_NOT_REQUESTED


class AccessCommentLength(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.ACCESS_COMMENT_LENGTH


class AccessExpiresOutOfRange(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.ACCESS_EXPIRES_OUT_OF_RANGE


class NotCollectivePrincipal(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = ErrorCode.NOT_COLLECTIVE_PRINCIPAL


class CollectiveNotVerified(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = ErrorCode.COLLECTIVE_NOT_VERIFIED


class EventServiceUnavailable(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.EVENT_SERVICE_UNAVAILABLE


class GrantNotFound(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.GRANT_NOT_FOUND


class GrantStateConflict(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.GRANT_STATE_CONFLICT


class GrantCooldown(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.GRANT_COOLDOWN


class TooManyRequests(VancedHTTPException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = ErrorCode.TOO_MANY_REQUESTS
