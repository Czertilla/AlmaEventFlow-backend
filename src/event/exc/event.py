from fastapi import status
from core.utils.exc.http import VancedHTTPException


class EventNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "EVENT_NOT_FOUND"


class ParticipationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "PARTICIPATION_NOT_FOUND"


class LocationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "LOCATION_NOT_FOUND"


class CollectiveNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "COLLECTIVE_NOT_FOUND"


class StageNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "STAGE_NOT_FOUND"


class RewardNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "REWARD_NOT_FOUND"


class LinkNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "LINK_NOT_FOUND"


class OrganizationNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "ORGANIZATION_NOT_FOUND"


class RoleNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "ROLE_NOT_FOUND"


class MemberNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "MEMBER_NOT_FOUND"


class PersonNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "PERSON_NOT_FOUND"


class AttendanceNotExistsException(VancedHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "ATTENDANCE_NOT_FOUND"