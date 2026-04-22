from fastapi import status
from core.utils.exc.http import VancedHTTPException


class UniversityNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = {"detail": "University not found"}
