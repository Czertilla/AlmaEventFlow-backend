from fastapi import status
from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class PassportNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.PASSPORT_NOT_FOUND


class PassportOwnershipException(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = ErrorCode.UNABLE_TO_OVERRIDE_PASSPORT_OWNERSHIP
