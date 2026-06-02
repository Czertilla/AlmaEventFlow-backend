from fastapi import status
from core.utils.exc.http import VancedHTTPException


class NonPersonalUserException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "ATTACHED_PERSON_REQUIRED"
