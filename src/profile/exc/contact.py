from fastapi import status
from core.utils.exc.http import VancedHTTPException


class ContactNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = {"detail": "Contact not found"}


class ContactOwnershipException(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = {"detail": "Unable to override contact ownership"}