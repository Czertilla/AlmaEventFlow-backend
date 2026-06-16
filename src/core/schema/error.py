from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import status
from pydantic import BaseModel


class ErrorCode(str, Enum):
    # Auth
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    INVALID_AUTHENTICATION_CREDENTIALS = "INVALID_AUTHENTICATION_CREDENTIALS"
    FORBIDDEN = "FORBIDDEN"
    REFRESH_TOKEN_MISSING = "REFRESH_TOKEN_MISSING"
    INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"
    LOGIN_BAD_CREDENTIALS = "LOGIN_BAD_CREDENTIALS"
    LOGIN_USER_NOT_VERIFIED = "LOGIN_USER_NOT_VERIFIED"

    # fastapi-users compat
    REGISTER_USER_ALREADY_EXISTS = "REGISTER_USER_ALREADY_EXISTS"
    REGISTER_INVALID_PASSWORD = "REGISTER_INVALID_PASSWORD"
    OAUTH_NOT_AVAILABLE_EMAIL = "OAUTH_NOT_AVAILABLE_EMAIL"
    OAUTH_USER_ALREADY_EXISTS = "OAUTH_USER_ALREADY_EXISTS"
    RESET_PASSWORD_BAD_TOKEN = "RESET_PASSWORD_BAD_TOKEN"
    RESET_PASSWORD_INVALID_PASSWORD = "RESET_PASSWORD_INVALID_PASSWORD"
    VERIFY_USER_BAD_TOKEN = "VERIFY_USER_BAD_TOKEN"
    VERIFY_USER_ALREADY_VERIFIED = "VERIFY_USER_ALREADY_VERIFIED"
    UPDATE_USER_EMAIL_ALREADY_EXISTS = "UPDATE_USER_EMAIL_ALREADY_EXISTS"
    UPDATE_USER_INVALID_PASSWORD = "UPDATE_USER_INVALID_PASSWORD"

    # User domain
    USERNAME_ALREADY_EXISTS = "USERNAME_ALREADY_EXISTS"
    INVITE_TOKEN_INVALID = "INVITE_TOKEN_INVALID"
    INVITE_TOKEN_EXPIRED = "INVITE_TOKEN_EXPIRED"
    PERSON_ALREADY_HAS_ACCOUNT = "PERSON_ALREADY_HAS_ACCOUNT"
    INVITE_PERSON_NOT_FOUND = "INVITE_PERSON_NOT_FOUND"

    # Profile domain
    ATTACHED_PERSON_REQUIRED = "ATTACHED_PERSON_REQUIRED"
    PERSON_NOT_FOUND = "PERSON_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    CONTACT_NOT_FOUND = "CONTACT_NOT_FOUND"
    DIET_NOT_FOUND = "DIET_NOT_FOUND"
    STUDENT_NOT_FOUND = "STUDENT_NOT_FOUND"
    PASSPORT_NOT_FOUND = "PASSPORT_NOT_FOUND"
    STUDENT_DEGREE_NOT_FOUND = "STUDENT_DEGREE_NOT_FOUND"
    STUDENT_GROUP_NOT_FOUND = "STUDENT_GROUP_NOT_FOUND"
    UNABLE_TO_OVERRIDE_CONTACT_OWNERSHIP = "UNABLE_TO_OVERRIDE_CONTACT_OWNERSHIP"
    UNABLE_TO_OVERRIDE_PASSPORT_OWNERSHIP = "UNABLE_TO_OVERRIDE_PASSPORT_OWNERSHIP"

    # Event domain
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    PARTICIPATION_NOT_FOUND = "PARTICIPATION_NOT_FOUND"
    COLLECTIVE_NOT_FOUND = "COLLECTIVE_NOT_FOUND"
    STAGE_NOT_FOUND = "STAGE_NOT_FOUND"
    REWARD_NOT_FOUND = "REWARD_NOT_FOUND"
    LINK_NOT_FOUND = "LINK_NOT_FOUND"
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    ATTENDANCE_NOT_FOUND = "ATTENDANCE_NOT_FOUND"
    NOT_COLLECTIVE_PRINCIPAL = "NOT_COLLECTIVE_PRINCIPAL"
    COLLECTIVE_NOT_VERIFIED = "COLLECTIVE_NOT_VERIFIED"
    COLLECTIVE_NOT_PARTICIPATING = "COLLECTIVE_NOT_PARTICIPATING"
    EVENT_ACTIVE_REQUIRES_DATE = "EVENT_ACTIVE_REQUIRES_DATE"
    NOT_MEMBER_PERSON = "NOT_MEMBER_PERSON"
    ATTENDANCE_ALREADY_VERIFIED = "ATTENDANCE_ALREADY_VERIFIED"
    CALENDAR_SUBSCRIPTION_NOT_FOUND = "CALENDAR_SUBSCRIPTION_NOT_FOUND"

    # Org domain
    UNIVERSITY_NOT_FOUND = "UNIVERSITY_NOT_FOUND"
    FACULTY_NOT_FOUND = "FACULTY_NOT_FOUND"
    ORGANIZATION_NOT_FOUND = "ORGANIZATION_NOT_FOUND"
    ADDRESS_NOT_FOUND = "ADDRESS_NOT_FOUND"

    # Geo domain
    LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"


class ErrorModel(BaseModel):
    detail: str | dict[str, str]


OpenAPIResponseType = dict[int, dict[str, Any]]


def _example_dict(
    code: ErrorCode, summary: str = "",
) -> dict[str, Any]:
    return {
        "summary": summary or code.value,
        "value": {"detail": code.value},
    }


def error_response(
    status_code: int,
    description: str,
    examples: dict[ErrorCode, dict[str, Any]] | None = None,
) -> OpenAPIResponseType:
    content: dict[str, Any] = {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/ErrorModel"},
        }
    }
    if examples:
        content["application/json"]["examples"] = {
            code.value: _example_dict(code, examples[code].get("summary", ""))
            for code in examples
        }
    return {status_code: {"description": description, "content": content}}


_ENTITY_MAP: dict[str, ErrorCode] = {
    "event": ErrorCode.EVENT_NOT_FOUND,
    "participation": ErrorCode.PARTICIPATION_NOT_FOUND,
    "collective": ErrorCode.COLLECTIVE_NOT_FOUND,
    "stage": ErrorCode.STAGE_NOT_FOUND,
    "reward": ErrorCode.REWARD_NOT_FOUND,
    "link": ErrorCode.LINK_NOT_FOUND,
    "role": ErrorCode.ROLE_NOT_FOUND,
    "member": ErrorCode.MEMBER_NOT_FOUND,
    "attendance": ErrorCode.ATTENDANCE_NOT_FOUND,
    "person": ErrorCode.PERSON_NOT_FOUND,
    "profile": ErrorCode.PROFILE_NOT_FOUND,
    "contact": ErrorCode.CONTACT_NOT_FOUND,
    "diet": ErrorCode.DIET_NOT_FOUND,
    "student": ErrorCode.STUDENT_NOT_FOUND,
    "passport": ErrorCode.PASSPORT_NOT_FOUND,
    "student_degree": ErrorCode.STUDENT_DEGREE_NOT_FOUND,
    "student_group": ErrorCode.STUDENT_GROUP_NOT_FOUND,
    "university": ErrorCode.UNIVERSITY_NOT_FOUND,
    "organization": ErrorCode.ORGANIZATION_NOT_FOUND,
    "faculty": ErrorCode.FACULTY_NOT_FOUND,
    "location": ErrorCode.LOCATION_NOT_FOUND,
    "address": ErrorCode.ADDRESS_NOT_FOUND,
}


def entity_not_found_responses(entity_name: str) -> OpenAPIResponseType:
    code = _ENTITY_MAP.get(entity_name)
    if code is None:
        return not_found_response(ErrorCode(entity_name.upper() + "_NOT_FOUND"))
    return not_found_response(code)


def not_found_response(code: ErrorCode) -> OpenAPIResponseType:
    return {
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorModel,
            "description": code.value,
            "content": {
                "application/json": {
                    "examples": {
                        code.value: _example_dict(code),
                    }
                }
            },
        }
    }


def auth_responses() -> OpenAPIResponseType:
    return {
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorModel,
            "description": "Missing or invalid authentication token",
            "content": {
                "application/json": {
                    "examples": {
                        ErrorCode.NOT_AUTHENTICATED.value: _example_dict(
                            ErrorCode.NOT_AUTHENTICATED,
                            "Missing or invalid authentication token",
                        ),
                        ErrorCode.INVALID_AUTHENTICATION_CREDENTIALS.value: _example_dict(
                            ErrorCode.INVALID_AUTHENTICATION_CREDENTIALS,
                            "Token decode failed",
                        ),
                    }
                }
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorModel,
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "examples": {
                        ErrorCode.FORBIDDEN.value: _example_dict(
                            ErrorCode.FORBIDDEN,
                            "Not superuser or not verified",
                        ),
                    }
                }
            },
        },
    }


def detail_response(status_code: int, code: ErrorCode) -> OpenAPIResponseType:
    return {
        status_code: {
            "model": ErrorModel,
            "description": code.value,
            "content": {
                "application/json": {
                    "examples": {
                        code.value: _example_dict(code),
                    }
                }
            },
        }
    }


def detail_400(code: ErrorCode) -> OpenAPIResponseType:
    return detail_response(status.HTTP_400_BAD_REQUEST, code)


def detail_401(code: ErrorCode) -> OpenAPIResponseType:
    return detail_response(status.HTTP_401_UNAUTHORIZED, code)


def detail_403(code: ErrorCode) -> OpenAPIResponseType:
    return detail_response(status.HTTP_403_FORBIDDEN, code)


def detail_404(code: ErrorCode) -> OpenAPIResponseType:
    return detail_response(status.HTTP_404_NOT_FOUND, code)


def detail_409(code: ErrorCode) -> OpenAPIResponseType:
    return detail_response(status.HTTP_409_CONFLICT, code)
