import ast
from pathlib import Path
from typing import Any

import pytest
from _registry import BUILT_BY_ROUTER, FORBIDDEN, MIGRATED_LAYERS, RESPONSES
from _snapshot import assert_matches

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
GOLDEN = Path(__file__).resolve().parent / "golden"


@pytest.mark.parametrize("name", RESPONSES)
def test_every_response_schema_is_paired_with_its_service_dto(
    name: str, behavior: dict[str, dict[str, Any]]
) -> None:
    package, pairs = RESPONSES[name]
    converting = set(behavior["responses"][name]["converting"])

    unpaired = converting - set(pairs) - BUILT_BY_ROUTER.get(package, set())

    assert not unpaired, (
        f"{sorted(unpaired)} convert from a DTO but are not registered in "
        "RESPONSES, so a service-layer change could break them unnoticed"
    )


@pytest.mark.parametrize("name", RESPONSES)
def test_service_dtos_render_through_the_response_schemas(
    name: str, behavior: dict[str, dict[str, Any]]
) -> None:
    package, _ = RESPONSES[name]

    assert_matches(
        GOLDEN / f"{name}_from_dto.json",
        behavior["responses"][name]["rendered"],
        package,
    )


@pytest.mark.parametrize("name", RESPONSES)
def test_every_sample_dto_is_accepted_by_its_response_schema(
    name: str, behavior: dict[str, dict[str, Any]]
) -> None:
    rendered = behavior["responses"][name]["rendered"]

    assert {key: record for key, record in rendered.items() if "error" in record} == {}


@pytest.mark.parametrize("name", RESPONSES)
def test_response_schemas_accept_every_value_the_dto_allows(
    name: str, behavior: dict[str, dict[str, Any]]
) -> None:
    assert behavior["responses"][name]["rejected"] == {}


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
