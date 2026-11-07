from copy import deepcopy
from typing import Any

from core.schema.error import (
    ErrorCode,
    OpenAPIResponseType,
    auth_responses,
    detail_404,
    detail_409,
    detail_response,
    error_response,
)

VISIBILITY_ERRORS: OpenAPIResponseType = {
    **detail_404(ErrorCode.VISIBILITY_FIELD_NOT_FOUND),
    **detail_409(ErrorCode.VISIBILITY_COOLDOWN),
    **detail_response(422, ErrorCode.VISIBILITY_OUT_OF_RANGE),
}


def _codes(status_code: int, *codes: ErrorCode) -> OpenAPIResponseType:
    return error_response(
        status_code,
        ", ".join(code.value for code in codes),
        {code: {} for code in codes},
    )


def merged(*parts: OpenAPIResponseType) -> OpenAPIResponseType:
    """Responses of one status code keep the examples of every part."""
    result: OpenAPIResponseType = {}
    for part in parts:
        for status_code, response in part.items():
            if status_code not in result:
                result[status_code] = deepcopy(response)
                continue
            content: dict[str, Any] = result[status_code].setdefault("content", {})
            examples = content.setdefault("application/json", {}).setdefault(
                "examples", {}
            )
            examples.update(
                response.get("content", {}).get("application/json", {}).get(
                    "examples", {}
                )
            )
            result[status_code]["description"] = ", ".join(sorted(examples))
    return result


_EVENT = _codes(503, ErrorCode.EVENT_SERVICE_UNAVAILABLE)
_LEAD = _codes(
    403, ErrorCode.NOT_COLLECTIVE_PRINCIPAL, ErrorCode.COLLECTIVE_NOT_VERIFIED
)
_LIMITED = _codes(429, ErrorCode.TOO_MANY_REQUESTS)

ACCESS_REQUEST_CREATE_ERRORS = merged(
    auth_responses(),
    _LEAD,
    _codes(
        422,
        ErrorCode.ACCESS_FIELD_NOT_GRANTABLE,
        ErrorCode.ACCESS_COMMENT_LENGTH,
        ErrorCode.ACCESS_EXPIRES_OUT_OF_RANGE,
    ),
    _LIMITED,
    _EVENT,
)
ACCESS_REQUEST_ERRORS = merged(
    auth_responses(), _codes(404, ErrorCode.ACCESS_REQUEST_NOT_FOUND)
)
ACCESS_EXPORT_ERRORS = merged(
    ACCESS_REQUEST_ERRORS,
    _LEAD,
    _codes(409, ErrorCode.ACCESS_REQUEST_EXPIRED),
    _codes(422, ErrorCode.ACCESS_FIELD_NOT_REQUESTED),
    _LIMITED,
    _codes(
        503, ErrorCode.EVENT_SERVICE_UNAVAILABLE, ErrorCode.PERSONAL_DATA_UNAVAILABLE
    ),
)
GRANT_ERRORS = merged(
    auth_responses(),
    _codes(404, ErrorCode.GRANT_NOT_FOUND),
    _codes(409, ErrorCode.GRANT_STATE_CONFLICT),
)
GRANT_APPROVE_ERRORS = merged(
    GRANT_ERRORS,
    _codes(
        409,
        ErrorCode.GRANT_STATE_CONFLICT,
        ErrorCode.ACCESS_REQUEST_EXPIRED,
        ErrorCode.GRANT_COOLDOWN,
    ),
)
