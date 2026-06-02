from fastapi import status
from core.utils.exc.http import VancedHTTPException


class UsernameAlreadyExists(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "USERNAME_ALREADY_EXISTS"


class InviteTokenInvalid(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "INVITE_TOKEN_INVALID"


class InviteTokenExpired(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "INVITE_TOKEN_EXPIRED"


class PersonAlreadyHasAccount(VancedHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "PERSON_ALREADY_HAS_ACCOUNT"
