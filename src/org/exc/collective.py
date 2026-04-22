from fastapi import status
from core.utils.exc.http import VancedHTTPException


class CollectiveNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = {"detail": "Collective not found"}
