from fastapi import status
from core.utils.exc.http import VancedHTTPException


class PassportNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = {"detail": "Passport not found"}

class PassportOwnershipException(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = {"detail": "Unable to override passport ownership"}
