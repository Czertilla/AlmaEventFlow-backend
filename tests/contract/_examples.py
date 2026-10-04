import dataclasses
import datetime
import enum
import importlib
import inspect
import json
import pkgutil
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ValidationError
from pydantic.errors import PydanticUserError

FIELD_OVERRIDES = {"timezone": "Europe/Moscow"}
VARIANTS = ("required", "full")
GENERATED = "<generated>"


def _string(schema: dict[str, Any], path: str) -> str:
    fmt = schema.get("format")
    if fmt == "uuid":
        return str(uuid5(NAMESPACE_URL, path))
    if fmt == "date-time":
        return "2026-01-01T10:00:00Z"
    if fmt == "date":
        return "2026-01-01"
    if fmt == "time":
        return "10:00:00"
    if fmt == "email":
        return "user@example.com"
    if fmt in ("uri", "url"):
        return "https://example.com/x"
    value = "x" * max(schema.get("minLength", 1), 1)
    return value[: schema["maxLength"]] if "maxLength" in schema else value


def _number(schema: dict[str, Any], integer: bool) -> int | float:
    value: int | float = 1 if integer else 1.5
    if "minimum" in schema:
        value = max(value, schema["minimum"])
    if "exclusiveMinimum" in schema:
        value = max(value, schema["exclusiveMinimum"] + 1)
    if "maximum" in schema:
        value = min(value, schema["maximum"])
    return value


def example(
    schema: dict[str, Any], defs: dict[str, Any], path: str, variant: str
) -> Any:
    if "$ref" in schema:
        return example(defs[schema["$ref"].rsplit("/", 1)[-1]], defs, path, variant)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            branches = [b for b in schema[key] if b.get("type") != "null"]
            return example(branches[0], defs, path, variant) if branches else None
    if "allOf" in schema:
        return example(schema["allOf"][0], defs, path, variant)
    kind = schema.get("type")
    if kind == "string":
        return _string(schema, path)
    if kind in ("integer", "number"):
        return _number(schema, kind == "integer")
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    if kind == "array":
        item = example(schema.get("items", {}), defs, path + "[]", variant)
        return [item] * max(schema.get("minItems", 1), 1)
    if kind == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", ()))
        result: dict[str, Any] = {}
        for name, sub in properties.items():
            if variant == "required" and name not in required:
                continue
            result[name] = (
                FIELD_OVERRIDES[name]
                if name in FIELD_OVERRIDES
                else example(sub, defs, f"{path}.{name}", variant)
            )
        if not properties and isinstance(schema.get("additionalProperties"), dict):
            result["key"] = example(
                schema["additionalProperties"], defs, path + ".key", variant
            )
        return result
    return None


def _encode(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        items = cast("set[Any]", value)
        return sorted(_encode(item) for item in items)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: _encode(getattr(value, f.name))
            for f in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        mapping = cast("dict[Any, Any]", value)
        return {str(k): _encode(v) for k, v in mapping.items()}
    if isinstance(value, (list, tuple)):
        sequence = cast("list[Any]", value)
        return [_encode(item) for item in sequence]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return f"<{type(value).__name__}>"


def characterize(model: type[BaseModel], variant: str) -> dict[str, Any]:
    try:
        schema = model.model_json_schema(by_alias=True, mode="validation")
    except PydanticUserError as exc:
        return {"unusable": exc.code}
    defs = schema.get("$defs", {})
    payload = example(schema, defs, model.__name__, variant)
    record: dict[str, Any] = {"input": payload}
    try:
        instance = model.model_validate(payload)
    except ValidationError as exc:
        record["error"] = sorted(
            f"{'.'.join(str(p) for p in err['loc'])}:{err['type']}"
            for err in exc.errors()
        )
        return record
    generated = {
        name: info
        for name, info in model.model_fields.items()
        if info.default_factory is not None and name not in instance.model_fields_set
    }
    record["dump"] = instance.model_dump(mode="json", by_alias=True)
    for name, info in generated.items():
        record["dump"][info.alias or name] = GENERATED
    record["fields_set"] = sorted(instance.model_fields_set)
    to_dto = getattr(instance, "to_dto", None)
    if to_dto is not None:
        dto = to_dto()
        dto_fields = {f.name for f in dataclasses.fields(dto)}
        sent = instance.model_dump()
        record["dto"] = {
            "mapped": {
                key: GENERATED if key in generated else _encode(getattr(dto, key))
                for key in sorted(sent)
                if key in dto_fields
            },
            "dropped": sorted(key for key in sent if key not in dto_fields),
        }
        if "fields_set" in dto_fields:
            record["dto"]["fields_set"] = sorted(dto.fields_set)
    return record


def schema_models(package: str) -> dict[str, type[BaseModel]]:
    root = importlib.import_module(package)
    models: dict[str, type[BaseModel]] = {}
    for info in pkgutil.iter_modules(root.__path__):
        module = importlib.import_module(f"{package}.{info.name}")
        for name, member in inspect.getmembers(module, inspect.isclass):
            if not (
                issubclass(member, BaseModel)
                and member.__module__ == module.__name__
            ):
                continue
            generic = member.__pydantic_generic_metadata__
            if generic["origin"] is not None:
                continue
            if generic["parameters"]:
                member = member[tuple(str for _ in generic["parameters"])]
            models[f"{info.name}.{name}"] = member
    return dict(sorted(models.items()))


def characterize_package(package: str) -> dict[str, Any]:
    return {
        name: {variant: characterize(model, variant) for variant in VARIANTS}
        for name, model in schema_models(package).items()
    }


def to_jsonable(data: Any) -> Any:
    return json.loads(json.dumps(data, default=str))
