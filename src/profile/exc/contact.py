from fastapi import status
from core.utils.exc.http import VancedHTTPException


class ContactNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "CONTACT_NOT_FOUND"


class ContactOwnershipException(VancedHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "UNABLE_TO_OVERRIDE_CONTACT_OWNERSHIP"