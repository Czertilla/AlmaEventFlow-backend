from fastapi import status
from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class DietNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.DIET_NOT_FOUND