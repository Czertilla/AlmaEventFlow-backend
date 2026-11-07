from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class VisibilityFieldNotFound(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.VISIBILITY_FIELD_NOT_FOUND


class VisibilityNotConfigurable(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.VISIBILITY_NOT_CONFIGURABLE


class VisibilityOutOfRange(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.VISIBILITY_OUT_OF_RANGE


class VisibilityCooldown(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.VISIBILITY_COOLDOWN
