import dataclasses
import importlib
import json
import sys
import types
import typing
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ValidationError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from _dto_examples import dto_example  # noqa: E402
from _examples import characterize_package, schema_models  # noqa: E402

from core.schema.v1.mixin.dto import FromDTOMixinV1  # noqa: E402


def _load(reference: str) -> type:
    module, name = reference.split(":")
    return getattr(importlib.import_module(module), name)


def _nullable_fields(dto_cls: type) -> list[str]:
    hints = typing.get_type_hints(dto_cls)
    names: list[str] = []
    for f in dataclasses.fields(dto_cls):
        hint = hints[f.name]
        origin = typing.get_origin(hint)
        if origin in (typing.Union, types.UnionType) and type(None) in typing.get_args(
            hint
        ):
            names.append(f.name)
    return names


def _rejected_nulls(model: type, dto_cls: type) -> list[str]:
    failures: list[str] = []
    base = dto_example(dto_cls)
    for name in _nullable_fields(dto_cls):
        variant = dataclasses.replace(base, **{name: None})
        try:
            cast("Any", model).from_dto(variant)
        except ValidationError as exc:
            codes = sorted({f"{'.'.join(str(p) for p in err['loc'])}" for err in exc.errors()})
            failures.append(f"{name}:{','.join(codes)}")
    return failures


def _responses(package: str, pairs: dict[str, str]) -> dict[str, Any]:
    models = schema_models(package)
    converting = sorted(
        key for key, model in models.items() if issubclass(model, FromDTOMixinV1)
    )
    rendered: dict[str, Any] = {}
    rejected: dict[str, list[str]] = {}
    for key, reference in pairs.items():
        dto_cls = _load(reference)
        failures = _rejected_nulls(models[key], dto_cls)
        if failures:
            rejected[key] = failures
        dto = dto_example(dto_cls)
        record: dict[str, Any] = {}
        try:
            response: BaseModel = cast("Any", models[key]).from_dto(dto)
        except ValidationError as exc:
            record["error"] = sorted(
                f"{'.'.join(str(p) for p in err['loc'])}:{err['type']}"
                for err in exc.errors()
            )
        else:
            record["response"] = response.model_dump(mode="json", by_alias=True)
        rendered[key] = record
    return {"converting": converting, "rendered": rendered, "rejected": rejected}


def main() -> None:
    mode, package, out = sys.argv[1:4]
    if mode == "characterize":
        data: Any = characterize_package(package)
    else:
        data = _responses(package, json.loads(sys.argv[4]))
    Path(out).write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


main()
