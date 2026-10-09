import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from _openapi import ROOT, SNAPSHOTS

PROBE = ["CMD", "python", "/app/core/utils/healthcheck.py"]
DOCKERFILE = re.compile(r"^src/(\w+)/Dockerfile$")


def _compose() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def _built_services() -> list[str]:
    services: dict[str, Any] = _compose()["services"]
    return sorted(
        name
        for name, spec in services.items()
        if DOCKERFILE.match(spec.get("build", {}).get("dockerfile", ""))
    )


def _served(service: str) -> set[str]:
    snapshots: list[Path] = (
        sorted(SNAPSHOTS.glob("*/v1.json"))
        if service == "aef"
        else [SNAPSHOTS / service / "v1.json"]
    )
    return {
        path
        for snapshot in snapshots
        for path in json.loads(snapshot.read_text(encoding="utf-8"))["paths"]
    }


@pytest.mark.parametrize("service", _built_services())
def test_every_service_container_probes_a_path_its_api_serves(service: str) -> None:
    healthcheck = _compose()["services"][service].get("healthcheck")

    assert healthcheck is not None, f"{service} has no healthcheck"
    assert healthcheck["test"][:3] == PROBE
    assert healthcheck["test"][3] in _served(service)
