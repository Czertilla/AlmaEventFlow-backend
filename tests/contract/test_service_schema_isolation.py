import ast
import re
from pathlib import Path
from typing import Any, cast

import pytest
from _dto_examples import dto_example
from _examples import schema_models
from _snapshot import assert_matches
from pydantic import BaseModel, ValidationError

from core.schema.v1.mixin.dto import FromDTOMixinV1
from event.dto.attendance import AttendanceDTO
from event.dto.calendar import (
    AvailableFeedsDTO,
    CalendarSubscriptionDTO,
    FeedDescriptorDTO,
)
from event.dto.collective import CollectiveSummaryDTO
from event.dto.event import EventDTO
from event.dto.link import LinkDTO
from event.dto.me import MeEventDTO
from event.dto.member import MemberDTO
from event.dto.participation import ParticipationDTO
from event.dto.reward import RewardDTO
from event.dto.role import RoleDTO, RolePreviewDTO
from event.dto.stage import StageDTO

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
GOLDEN = Path(__file__).resolve().parent / "golden"

RESPONSES = {
    "event_v1": (
        "event.api.v1.schema",
        {
            "attendance.AttendanceRead": AttendanceDTO,
            "collective.MyCollectiveRead": CollectiveSummaryDTO,
            "event.EventRead": EventDTO,
            "link.LinkRead": LinkDTO,
            "me.MeEventRead": MeEventDTO,
            "member.MemberRead": MemberDTO,
            "participation.ParticipationRead": ParticipationDTO,
            "reward.RewardRead": RewardDTO,
            "role.RolePreview": RolePreviewDTO,
            "role.RoleRead": RoleDTO,
            "stage.StageRead": StageDTO,
        },
    ),
    "event_v2": (
        "event.api.v2.schema",
        {
            "calendar.AvailableFeeds": AvailableFeedsDTO,
            "calendar.FeedDescriptor": FeedDescriptorDTO,
            "calendar.SubscriptionRead": CalendarSubscriptionDTO,
        },
    ),
}
BUILT_BY_ROUTER = {"event.api.v2.schema": {"calendar.SubscriptionCreated"}}

MIGRATED_LAYERS = {
    "event": ("service", "repository", "uow", "dto", "models"),
    "core": ("dto", "service", "uow", "database"),
}
FORBIDDEN = {
    "event": (
        re.compile(r"^event\.api(\.|$)"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "core": (re.compile(r"^core\.schema\.v\d+"),),
}


@pytest.mark.parametrize("name", RESPONSES)
def test_every_response_schema_is_paired_with_its_service_dto(
    name: str,
) -> None:
    package, pairs = RESPONSES[name]
    converting = {
        key
        for key, model in schema_models(package).items()
        if issubclass(model, FromDTOMixinV1)
    }

    unpaired = converting - set(pairs) - BUILT_BY_ROUTER.get(package, set())

    assert not unpaired, (
        f"{sorted(unpaired)} convert from a DTO but are not registered in "
        "RESPONSES, so a service-layer change could break them unnoticed"
    )


@pytest.mark.parametrize("name", RESPONSES)
def test_service_dtos_render_through_the_response_schemas(
    name: str,
) -> None:
    package, pairs = RESPONSES[name]
    models = schema_models(package)
    rendered = {}
    for key, dto_cls in pairs.items():
        dto = dto_example(dto_cls)
        record: dict[str, object] = {}
        try:
            response = cast("Any", models[key]).from_dto(dto)
        except ValidationError as exc:
            record["error"] = sorted(
                f"{'.'.join(str(p) for p in err['loc'])}:{err['type']}"
                for err in exc.errors()
            )
        else:
            record["response"] = cast("BaseModel", response).model_dump(
                mode="json", by_alias=True
            )
        rendered[key] = record

    assert_matches(GOLDEN / f"{name}_from_dto.json", rendered, package)


def _imports(path: Path) -> list[str]:
    module = ".".join(path.relative_to(SRC).with_suffix("").parts)
    package_parts = module.split(".")[:-1]
    found: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package_parts[: len(package_parts) - node.level + 1]
                base = ".".join([*anchor, base] if base else anchor)
            found.append(base)
            found.extend(f"{base}.{alias.name}" for alias in node.names)
    return found


@pytest.mark.parametrize("service", MIGRATED_LAYERS)
def test_service_layer_does_not_depend_on_api_schemas(service: str) -> None:
    violations: list[str] = []
    for layer in MIGRATED_LAYERS[service]:
        for path in sorted((SRC / service / layer).rglob("*.py")):
            for imported in _imports(path):
                if any(rule.match(imported) for rule in FORBIDDEN[service]):
                    violations.append(
                        f"{path.relative_to(SRC)} imports {imported}"
                    )

    assert not violations, "\n".join(violations)
