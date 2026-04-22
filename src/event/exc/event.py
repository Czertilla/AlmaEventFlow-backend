from core.utils.exc.http import BaseHTTPException


class EventNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Event not found"


class ParticipationNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Participation not found"


class LocationNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Location not found"


class CollectiveNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Collective not found"


class StageNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Stage not found"


class RewardNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Reward not found"


class LinkNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Link not found"


class OrganizationNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Organization not found"


class RoleNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Role not found"


class MemberNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Member not found"


class PersonNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Person not found"


class AttendanceNotExistsException(BaseHTTPException):
    status_code = 404
    detail = "Attendance not found"