from fastapi import status
from core.utils.exc.http import VancedHTTPException


class ProfileNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "PROFILE_NOT_FOUND"