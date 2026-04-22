from fastapi import status
from core.utils.exc.http import VancedHTTPException


class StudentNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = {"detail": "Student not found"}