from fastapi import status
from core.utils.exc.http import VancedHTTPException


class PersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "PERSON_NOT_FOUND"
