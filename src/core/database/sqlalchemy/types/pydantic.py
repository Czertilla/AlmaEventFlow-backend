from typing import Any, cast

from pydantic import TypeAdapter
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator


class PydanticJSONB(TypeDecorator[Any]):
    impl = JSONB
    cache_ok = True

    def __init__(self, pydantic_model: type[Any]) -> None:
        super().__init__()
        self.pydantic_model = pydantic_model
        self._adapter: TypeAdapter[Any] = TypeAdapter(pydantic_model)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return cast("dict[str, Any]", value)
        return self._adapter.dump_python(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return self._adapter.validate_python(value)
