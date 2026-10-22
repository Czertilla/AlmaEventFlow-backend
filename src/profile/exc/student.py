from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class StudentNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.STUDENT_NOT_FOUND


class StudentGroupNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.STUDENT_GROUP_NOT_FOUND


class StudentDegreeNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.STUDENT_DEGREE_NOT_FOUND


class StudentDegreeAlreadyExistsException(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.STUDENT_DEGREE_ALREADY_EXISTS


class StudentDegreeInUseException(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.STUDENT_DEGREE_IN_USE


class StudentGroupAlreadyExistsException(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.STUDENT_GROUP_ALREADY_EXISTS


class StudentGroupInUseException(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.STUDENT_GROUP_IN_USE


class StudentAlreadyExistsException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.STUDENT_ALREADY_EXISTS
