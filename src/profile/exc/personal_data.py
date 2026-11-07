from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class PersonalDataUnavailable(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.PERSONAL_DATA_UNAVAILABLE


class PersonKeyAbsent(VancedHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = ErrorCode.PERSON_KEY_ABSENT


class DestroyNotConfirmed(VancedHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = ErrorCode.DESTROY_NOT_CONFIRMED
