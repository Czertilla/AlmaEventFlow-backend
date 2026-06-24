from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class ClientNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.NOTIFY_CLIENT_NOT_FOUND


class TransportNotSupportedException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.NOTIFY_TRANSPORT_NOT_SUPPORTED


class WebPushClientInvalidException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.WEBPUSH_CLIENT_INVALID


class WebPushNotConfiguredException(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.WEBPUSH_NOT_CONFIGURED
