from fastapi import status
from core.utils.exc.http import VancedHTTPException


class PersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "PERSON_NOT_FOUND"