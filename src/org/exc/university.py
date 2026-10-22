from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class UniversityNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.UNIVERSITY_NOT_FOUND


class UniversityHasFacultiesException(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.UNIVERSITY_HAS_FACULTIES
