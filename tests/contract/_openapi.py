import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

from _snapshot import dump_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOTS = HERE / "snapshots"
SERVICES = ("bot", "event", "geo", "mail", "notify", "org", "profile", "user")
PINNED_ENV = {
    "DB_DBMS": "postgres",
    "DB_HOST": "localhost",
    "DB_PORT": "5433",
    "DB_USER": "test",
    "DB_PASS": "test",
    "MONOLITH": "true",
    "APP_ARCHITECTURE": "monolith",
    "IN_MEMORY_BROKER": "true",
    "GEO_LIVE_FETCH": "false",
    "APP_HOST": "localhost",
    "S3_BUCKET_NAME": "test",
    "S3_ACCESS_KEY": "test",
    "S3_SECRET_KEY": "test",
    "MAX_PAGE_SIZE": "100",
    "OAUTH_GOOGLE_CLIENT_ID": "contract",
    "OAUTH_GOOGLE_CLIENT_SECRET": "contract",
    "BOT_TG_TOKEN": "123456789:AAContractSnapshotTokenOnly_0000000",
    "MAIL_ADMIN_EMAIL": "admin@example.com",
    "MAIL_ADMIN_USERNAME": "contract",
    "MAIL_ADMIN_PASSWORD": "contract",
}

_VERSION_RE = re.compile(r"^/[^/]+/(v\d+)(?:/|$)")
_REF_PREFIX = "#/components/"


def snapshot_path(service: str, version: str) -> Path:
    return SNAPSHOTS / service / f"{version}.json"


def snapshot_files() -> list[tuple[str, str]]:
    return sorted(
        (path.parent.name, path.stem)
        for path in SNAPSHOTS.glob("*/*.json")
    )


def _generate(service: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "openapi.json"
        subprocess.run(
            [sys.executable, str(HERE / "_dump_openapi.py"), service, str(out)],
            check=True,
            cwd=ROOT,
            env={**os.environ, **PINNED_ENV},
            capture_output=True,
        )
        return json.loads(out.read_text(encoding="utf-8"))


def _collect_refs(node: Any, found: set[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        mapping = cast("dict[str, Any]", node)
        for key, value in mapping.items():
            if key == "$ref" and isinstance(value, str):
                if value.startswith(_REF_PREFIX):
                    section, name = value[len(_REF_PREFIX):].split("/", 1)
                    found.add((section, name))
            else:
                _collect_refs(value, found)
    elif isinstance(node, list):
        for item in cast("list[Any]", node):
            _collect_refs(item, found)


def _reachable_components(
    paths: dict[str, Any], components: dict[str, Any]
) -> dict[str, Any]:
    pending: set[tuple[str, str]] = set()
    _collect_refs(paths, pending)
    seen: set[tuple[str, str]] = set()
    while pending:
        ref = pending.pop()
        if ref in seen:
            continue
        seen.add(ref)
        section, name = ref
        target = components.get(section, {}).get(name)
        if target is not None:
            _collect_refs(target, pending)
    result: dict[str, dict[str, Any]] = {}
    for section, name in sorted(seen):
        result.setdefault(section, {})[name] = components[section][name]
    return result


def split_by_version(openapi: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for path, item in openapi.get("paths", {}).items():
        match = _VERSION_RE.match(path)
        version = match.group(1) if match else "unversioned"
        grouped.setdefault(version, {})[path] = item
    components = openapi.get("components", {})
    return {
        version: {
            "paths": paths,
            "components": _reachable_components(paths, components),
        }
        for version, paths in grouped.items()
    }


def generate_all() -> dict[str, dict[str, dict[str, Any]]]:
    with ThreadPoolExecutor(max_workers=len(SERVICES)) as pool:
        specs = list(pool.map(_generate, SERVICES))
    return {
        service: split_by_version(spec)
        for service, spec in zip(SERVICES, specs, strict=True)
    }


def write_snapshots(current: dict[str, dict[str, dict[str, Any]]]) -> None:
    wanted: set[Path] = set()
    for service, versions in current.items():
        for version, contract in versions.items():
            path = snapshot_path(service, version)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dump_json(contract), encoding="utf-8")
            wanted.add(path)
    for path in SNAPSHOTS.glob("*/*.json"):
        if path not in wanted:
            path.unlink()
