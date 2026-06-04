from fastapi import status
from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException


class EventNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.EVENT_NOT_FOUND


class ParticipationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.PARTICIPATION_NOT_FOUND


class LocationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.LOCATION_NOT_FOUND


class CollectiveNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.COLLECTIVE_NOT_FOUND


class StageNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.STAGE_NOT_FOUND


class RewardNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.REWARD_NOT_FOUND


class LinkNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.LINK_NOT_FOUND


class OrganizationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.ORGANIZATION_NOT_FOUND


class RoleNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.ROLE_NOT_FOUND


class MemberNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.MEMBER_NOT_FOUND


class PersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.PERSON_NOT_FOUND


class AttendanceNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = ErrorCode.ATTENDANCE_NOT_FOUND