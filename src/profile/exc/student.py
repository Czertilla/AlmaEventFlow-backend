from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class StudentNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.STUDENT_NOT_FOUND


class StudentAlreadyExistsException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.STUDENT_ALREADY_EXISTS
