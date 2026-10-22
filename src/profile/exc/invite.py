from fastapi import status

from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class InviteSigningNotConfigured(VancedHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = ErrorCode.INVITE_SIGNING_NOT_CONFIGURED
