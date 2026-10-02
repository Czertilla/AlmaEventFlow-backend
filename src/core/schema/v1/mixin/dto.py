from dataclasses import fields as dataclass_fields
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


class FromDTOMixinV1:
    @classmethod
    def from_dto(cls, dto: object) -> Self:
        model = cast("type[BaseModel]", cls)
        return cast("Self", model.model_validate(dto, from_attributes=True))


class ToDTOMixinV1:
    __dto_cls__: ClassVar[type["DataclassInstance"]]

    def to_dto(self) -> Any:
        model = cast("BaseModel", self)
        dto_cls = self.__dto_cls__
        field_names = {f.name for f in dataclass_fields(dto_cls)}
        data = {k: v for k, v in model.model_dump().items() if k in field_names}
        if "fields_set" in field_names:
            data["fields_set"] = frozenset(model.model_fields_set)
        return dto_cls(**data)
