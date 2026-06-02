from fastapi import status
from core.utils.exc.http import VancedHTTPException


class PassportNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "PASSPORT_NOT_FOUND"


class PassportOwnershipException(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "UNABLE_TO_OVERRIDE_PASSPORT_OWNERSHIP"
