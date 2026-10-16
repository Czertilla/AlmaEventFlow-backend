import re
from typing import Any

import pytest
import yaml
from _openapi import ROOT

ROUTED = [
    "aef",
    "user",
    "mail",
    "profile",
    "event",
    "org",
    "geo",
    "notify",
    "bot",
    "frontend",
]
MICROSERVICES = ["user", "mail", "profile", "event", "org", "geo", "notify"]
PROBE = "/app/core/utils/healthcheck.py"


def _compose() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def _labels(service: str) -> dict[str, str]:
    pairs = (label.split("=", 1) for label in _compose()["services"][service]["labels"])
    return dict(pairs)


def _failover() -> dict[str, Any]:
    path = ROOT / "docker" / "traefik" / "dynamic" / "failover.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["http"]["services"]


@pytest.mark.parametrize("service", ROUTED)
def test_a_routed_service_is_guarded_and_probed_like_its_container(
    service: str,
) -> None:
    labels = _labels(service)
    spec = _compose()["services"][service]
    prefix = f"traefik.http.services.{service}.loadbalancer.healthcheck"

    assert (
        labels[f"traefik.http.routers.{service}.service"] == f"{service}-guarded@file"
    )
    assert labels[f"{prefix}.interval"] == "3s"
    assert labels[f"{prefix}.unhealthyinterval"] == "1s"
    assert labels[f"{prefix}.timeout"] == "2s"
    if "healthcheck" in spec:
        assert labels[f"{prefix}.path"] == spec["healthcheck"]["test"][-1]
    else:
        assert labels[f"{prefix}.path"] == "/"
    failover = _failover()[f"{service}-guarded"]["failover"]
    assert failover == {
        "service": f"{service}@docker",
        "fallback": "outage@docker",
        "healthCheck": {},
    }


def test_the_fallback_service_is_probed_because_failover_needs_it() -> None:
    labels = _labels("status-page")

    assert (
        labels["traefik.http.services.outage.loadbalancer.healthcheck.path"]
        == "/healthz"
    )


def test_traefik_keeps_empty_services_and_reads_the_failover_definitions() -> None:
    traefik = _compose()["services"]["traefik"]

    assert "--providers.docker.allowEmptyServices=true" in traefik["command"]
    assert "--providers.file.directory=/etc/traefik/dynamic" in traefik["command"]
    assert "./docker/traefik/dynamic:/etc/traefik/dynamic:ro" in traefik["volumes"]


def test_the_outage_router_is_the_last_resort_for_every_prefix() -> None:
    labels = _labels("status-page")
    rule = labels["traefik.http.routers.outage.rule"]
    prefixes = {
        prefix
        for service in [*MICROSERVICES, "bot"]
        for prefix in re.findall(
            r"PathPrefix\(`(/[a-z]+)`\)",
            _labels(service)[f"traefik.http.routers.{service}.rule"],
        )
    }

    assert prefixes == set(re.findall(r"PathPrefix\(`(/[a-z]+)`\)", rule))
    assert labels["traefik.http.routers.outage.priority"] == "1"
    assert labels["traefik.http.routers.outage-web.priority"] == "1"
    assert (
        labels["traefik.http.routers.outage-web.rule"]
        == _labels("frontend")["traefik.http.routers.frontend.rule"]
    )


def test_the_maintenance_mode_outranks_every_router_and_only_exists_on_demand() -> None:
    spec = _compose()["services"]["maintenance"]
    labels = _labels("maintenance")

    assert spec["profiles"] == ["maintenance"]
    assert int(labels["traefik.http.routers.maintenance.priority"]) >= 1_000_000
    assert (
        labels["traefik.http.routers.maintenance.rule"]
        == _labels("aef")["traefik.http.routers.aef.rule"]
    )
    assert spec["environment"]["STATUS_PAGE"] == "maintenance"
    assert (
        _compose()["services"]["status-page"]["environment"]["STATUS_PAGE"] == "outage"
    )


def test_the_mode_is_a_profile_and_the_bot_and_the_kafka_ui_are_opt_in() -> None:
    services = _compose()["services"]
    profiles = {name: set(spec.get("profiles", [])) for name, spec in services.items()}

    assert profiles["aef"] == {"monolith"}
    assert profiles["bot"] == {"bot"}
    assert profiles["kafka-ui"] == {"tools"}
    assert profiles["photon"] == {"photon"}
    assert all(profiles[name] == {"microservices"} for name in MICROSERVICES)
    always_on = {name for name, found in profiles.items() if not found}
    assert always_on == {
        "pg",
        "kafka",
        "redis",
        "frontend",
        "traefik",
        "status-page",
    }


def test_the_own_photon_is_internal_persistent_and_never_routed() -> None:
    spec = _compose()["services"]["photon"]

    assert "labels" not in spec
    assert "ports" not in spec
    assert spec["expose"] == ["2322"]
    assert spec["volumes"] == ["photon-data:/photon/data"]
    assert "photon-data" in _compose()["volumes"]
    assert spec["environment"]["REGION"].startswith("${PHOTON_REGION:-")


def test_the_deploy_script_knows_every_opt_in_profile_of_the_compose_file() -> None:
    script = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    extras = re.search(r'^EXTRAS="([^"]*)"', script, re.MULTILINE)
    services = _compose()["services"]
    opt_in = {
        profile
        for spec in services.values()
        for profile in spec.get("profiles", [])
        if profile not in {"monolith", "microservices", "maintenance"}
    }

    assert extras is not None
    assert set(extras.group(1).split()) == opt_in


@pytest.mark.parametrize("service", MICROSERVICES)
def test_a_microservice_always_uses_kafka_not_a_shared_broker(
    service: str,
) -> None:
    spec = _compose()["services"][service]

    assert spec["environment"]["IN_MEMORY_BROKER"] == "false"
    assert spec["depends_on"]["kafka"]["condition"] == "service_healthy"
    assert spec["healthcheck"]["test"][:2] == ["CMD", "python"]
    assert PROBE in spec["healthcheck"]["test"]
