from fastapi import status
from core.utils.exc.http import VancedHTTPException


class FacultyNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "FACULTY_NOT_FOUND"
