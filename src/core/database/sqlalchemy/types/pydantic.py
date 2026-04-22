from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

class PydanticJSONB(TypeDecorator):
    impl = JSONB
    cache_ok = True

    def __init__(self, pydantic_model: type[BaseModel]):
        super().__init__()
        self.pydantic_model = pydantic_model

    def process_bind_param(self, value, dialect):
        if value is None: 
            return None
        return value.model_dump() if isinstance(value, BaseModel) else value

    def process_result_value(self, value, dialect):
        if value is None: 
            return None
        return self.pydantic_model.model_validate(value)
