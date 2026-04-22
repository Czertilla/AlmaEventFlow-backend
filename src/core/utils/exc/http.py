from typing import Any
from uuid import UUID, uuid4
from fastapi import HTTPException


class VancedHTTPException(HTTPException):
    status_code: int = None
    detail: Any | dict[str, Any] = None
    headers: dict[str, Any] = {}

    def __init__(
        self,
        status_code=None,
        detail=None,
        headers: dict[str, str] = {},
        *,
        err_id: UUID | None = None,
    ):
        self.id = err_id or uuid4()
        headers.update({"err-id": str(self.id)})
        super().__init__(
            status_code or self.status_code,
            detail or self.detail,
            headers | self.headers,
        )
