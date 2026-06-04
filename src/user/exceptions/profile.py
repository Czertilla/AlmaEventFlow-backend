from fastapi import status
from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class InvitePersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = ErrorCode.INVITE_PERSON_NOT_FOUND