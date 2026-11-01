import ast
from pathlib import Path

API = Path(__file__).resolve().parents[2] / "src" / "profile" / "api"
FORBIDDEN = ("profile.models", "profile.repository", "sqlalchemy")


def _imports(path: Path) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def test_the_api_layer_reads_personal_data_only_through_services() -> None:
    violations = [
        f"{path.relative_to(API.parent)}: {name}"
        for path in sorted(API.rglob("*.py"))
        for name in _imports(path)
        if any(name == bad or name.startswith(f"{bad}.") for bad in FORBIDDEN)
    ]

    assert violations == []
