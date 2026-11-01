from core.schema.error import (
    ErrorCode,
    OpenAPIResponseType,
    detail_404,
    detail_409,
    detail_response,
)

VISIBILITY_ERRORS: OpenAPIResponseType = {
    **detail_404(ErrorCode.VISIBILITY_FIELD_NOT_FOUND),
    **detail_409(ErrorCode.VISIBILITY_COOLDOWN),
    **detail_response(422, ErrorCode.VISIBILITY_OUT_OF_RANGE),
}
