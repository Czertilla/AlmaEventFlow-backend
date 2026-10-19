import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import String, cast

ID_FRAGMENT = re.compile(r"[0-9a-fA-F-]{6,36}")
MAX_INT_DIGITS = 18


class IdentityFilterMixin(BaseModel):
    id: UUID | None = None
    id__in: list[UUID] | None = None


def id_search_clause(model: Any, term: str) -> Any | None:
    """A clause for the row whose ``id`` the text names, when it can name one."""
    column = getattr(model, "id", None)
    column_type = getattr(column, "type", None)
    if column_type is None:
        return None
    try:
        kind = column_type.python_type
    except NotImplementedError:
        return None
    text = term.strip()
    if kind is UUID:
        try:
            return column == UUID(text)
        except ValueError:
            if ID_FRAGMENT.fullmatch(text):
                return cast(column, String).ilike(f"{text}%")
            return None
    if kind is int and text.isdecimal() and len(text) <= MAX_INT_DIGITS:
        return cast(column, String) == str(int(text))
    return None
