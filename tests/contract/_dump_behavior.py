import importlib
import json
import sys
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


def _responses(package: str, pairs: dict[str, str]) -> dict[str, Any]:
    models = schema_models(package)
    converting = sorted(
        key for key, model in models.items() if issubclass(model, FromDTOMixinV1)
    )
    rendered: dict[str, Any] = {}
    for key, reference in pairs.items():
        dto = dto_example(_load(reference))
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
    return {"converting": converting, "rendered": rendered}


def main() -> None:
    mode, package, out = sys.argv[1:4]
    if mode == "characterize":
        data: Any = characterize_package(package)
    else:
        data = _responses(package, json.loads(sys.argv[4]))
    Path(out).write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


main()
