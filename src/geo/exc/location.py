from fastapi import status
from core.utils.exc.http import VancedHTTPException


class LocationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "LOCATION_NOT_FOUND"