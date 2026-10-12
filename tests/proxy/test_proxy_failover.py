import os
import re
import socket
import subprocess
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TRAEFIK_IMAGE = os.environ.get("PROXY_TEST_TRAEFIK_IMAGE", "")
NGINX_IMAGE = os.environ.get("PROXY_TEST_NGINX_IMAGE", "nginx:1.27-alpine")
API = "api.localhost"
WEB = "localhost"
ORIGIN = "http://localhost:5173"
MODES = {"monolith": ["aef"], "microservices": ["user", "notify"]}
STUB = """server {{
  listen 8000;
  listen 80;
  default_type application/json;
  location = {health} {{
    if (-f /tmp/down) {{ return 500 '{{"status":"broken"}}'; }}
    return 200 '{{"status":"ok"}}';
  }}
  location = /notify/v1/webpush/vapid-public-key {{
    return 503 '{{"detail":"WEBPUSH_NOT_CONFIGURED"}}';
  }}
  location / {{ return 200 '{{"from":"{name}"}}'; }}
}}
"""


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args], check=check, capture_output=True, text=True, timeout=300
    )


def _has_image(image: str) -> bool:
    return (
        bool(image) and _docker("image", "inspect", image, check=False).returncode == 0
    )


def _bind(source: Path, target: str) -> dict[str, Any]:
    return {
        "type": "bind",
        "source": source.as_posix(),
        "target": target,
        "read_only": True,
    }


def _labels(labels: list[str]) -> list[str]:
    result: list[str] = []
    for label in labels:
        if ".tls." in label:
            continue
        label = label.replace("${API_SUBDOMAIN}.${APP_HOST}", API).replace(
            "${APP_HOST}", WEB
        )
        result.append(label.replace("websecure", "web"))
    return result


def _health_path(service: dict[str, Any]) -> str:
    for label in service["labels"]:
        match = re.search(r"\.healthcheck\.path=(.+)$", label)
        if match:
            return match.group(1)
    raise AssertionError("no health path")


def _stack(mode: str, tmp: Path, port: int) -> dict[str, Any]:
    real = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services: dict[str, Any] = {}
    flags = [
        flag
        for flag in real["services"]["traefik"]["command"]
        if flag.startswith("--providers.")
    ]
    services["traefik"] = {
        "image": TRAEFIK_IMAGE,
        "command": [*flags, "--entryPoints.web.address=:80"],
        "ports": [f"127.0.0.1:{port}:80"],
        "volumes": [
            {
                "type": "bind",
                "source": "/var/run/docker.sock",
                "target": "/var/run/docker.sock",
                "read_only": True,
            },
            _bind(ROOT / "docker" / "traefik" / "dynamic", "/etc/traefik/dynamic"),
        ],
    }
    for name in [*MODES[mode], "frontend"]:
        spec = real["services"][name]
        health = _health_path(spec)
        conf = tmp / f"{name}.conf"
        conf.write_text(STUB.format(health=health, name=name), encoding="utf-8")
        services[name] = {
            "image": NGINX_IMAGE,
            "volumes": [_bind(conf, "/etc/nginx/templates/default.conf.template")],
            "healthcheck": {
                "test": [
                    "CMD-SHELL",
                    f"wget -qO- http://127.0.0.1{health} >/dev/null 2>&1 || exit 1",
                ],
                "interval": "2s",
                "timeout": "2s",
                "retries": 2,
            },
            "labels": _labels(spec["labels"]),
        }
    for name in ("status-page", "maintenance"):
        spec = real["services"][name]
        services[name] = {
            "image": NGINX_IMAGE,
            "environment": {
                k: str(v).replace("${APP_HOST}", WEB)
                for k, v in spec["environment"].items()
            },
            "volumes": [
                _bind(
                    ROOT / "docker" / "status" / "default.conf.template",
                    "/etc/nginx/templates/default.conf.template",
                ),
                _bind(ROOT / "docker" / "status" / "pages", "/usr/share/nginx/status"),
            ],
            "labels": _labels(spec["labels"]),
        }
        if "healthcheck" in spec:
            services[name]["healthcheck"] = {**spec["healthcheck"], "interval": "2s"}
        if "profiles" in spec:
            services[name]["profiles"] = spec["profiles"]
    return {"services": services}


class Stack:
    def __init__(self, mode: str, tmp: Path, port: int) -> None:
        self.mode = mode
        self.port = port
        self.project = f"aefproxy{uuid.uuid4().hex[:8]}"
        self.file = tmp / "docker-compose.yml"
        self.file.write_text(yaml.safe_dump(_stack(mode, tmp, port)), encoding="utf-8")
        self.target = MODES[mode][0]
        self.app503 = "aef" if mode == "monolith" else "notify"

    def compose(self, *args: str) -> None:
        _docker(
            "compose",
            "-p",
            self.project,
            "-f",
            str(self.file),
            "--profile",
            "maintenance",
            *args,
        )

    def get(
        self,
        path: str,
        host: str = API,
        accept: str = "application/json",
        origin: str | None = None,
        method: str = "GET",
    ) -> httpx.Response:
        headers = {"Host": host, "Accept": accept}
        if origin:
            headers["Origin"] = origin
        if method == "OPTIONS":
            headers["Access-Control-Request-Method"] = "GET"
            headers["Access-Control-Request-Headers"] = "authorization"
        try:
            return httpx.request(
                method,
                f"http://127.0.0.1:{self.port}{path}",
                headers=headers,
                timeout=5,
            )
        except httpx.HTTPError:
            return httpx.Response(0)

    def until(self, check: Callable[[], bool], what: str, timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.5)
        pytest.fail(f"timed out waiting for {what}")

    def status(self, path: str, **kwargs: Any) -> int:
        return self.get(path, **kwargs).status_code

    def reported(self, path: str) -> str | None:
        response = self.get(path)
        if response.status_code != 503:
            return None
        try:
            return response.json().get("status")
        except ValueError:
            return None

    def healthy(self) -> None:
        self.until(lambda: self.status("/user/v1/ping") == 200, "the api to answer")
        self.until(lambda: self.status("/", host=WEB) == 200, "the frontend to answer")


@pytest.fixture(scope="module", params=sorted(MODES))
def stack(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Stack]:
    if _docker("info", check=False).returncode != 0:
        pytest.skip("docker is not available")
    for image in (TRAEFIK_IMAGE, NGINX_IMAGE):
        if not _has_image(image):
            pytest.skip(
                f"image {image!r} is not available locally "
                "(set PROXY_TEST_TRAEFIK_IMAGE / PROXY_TEST_NGINX_IMAGE)"
            )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    built = Stack(request.param, tmp_path_factory.mktemp(request.param), port)
    try:
        built.compose(
            "up",
            "-d",
            "--wait",
            "traefik",
            "status-page",
            "frontend",
            *MODES[request.param],
        )
        built.healthy()
        yield built
    finally:
        _docker(
            "compose",
            "-p",
            built.project,
            "-f",
            str(built.file),
            "--profile",
            "maintenance",
            "down",
            "-v",
            "--remove-orphans",
            check=False,
        )


def test_a_healthy_stack_serves_the_api_and_the_app_keeps_its_own_503(
    stack: Stack,
) -> None:
    own = stack.get("/notify/v1/webpush/vapid-public-key")

    assert stack.status("/user/v1/ping") == 200
    assert (own.status_code, own.json()) == (503, {"detail": "WEBPUSH_NOT_CONFIGURED"})


def test_a_stopped_service_is_answered_with_the_outage_page_for_both_clients(
    stack: Stack,
) -> None:
    stack.compose("stop", stack.target)
    try:
        stack.until(
            lambda: stack.get("/user/v1/ping").status_code == 503, "the outage answer"
        )
        machine = stack.get("/user/v1/ping")
        browser = stack.get("/user/v1/ping", accept="text/html,application/xhtml+xml")
        assert machine.json()["status"] == "unavailable"
        assert machine.headers["content-type"].startswith("application/json")
        assert machine.headers["retry-after"] == "30"
        assert browser.status_code == 503
        assert "text/html" in browser.headers["content-type"]
        assert "по техническим причинам" in browser.text
        assert stack.status("/", host=WEB) == 200
    finally:
        stack.compose("start", stack.target)
        stack.healthy()


def test_a_removed_service_is_answered_with_the_outage_page_too(stack: Stack) -> None:
    stack.compose("rm", "-sf", stack.target)
    try:
        stack.until(
            lambda: stack.get("/user/v1/ping").status_code == 503, "the outage answer"
        )
        assert stack.get("/user/v1/ping").json()["status"] == "unavailable"
    finally:
        stack.compose("up", "-d", "--wait", stack.target)
        stack.healthy()


def test_a_running_service_that_fails_its_health_probe_is_taken_out(
    stack: Stack,
) -> None:
    _docker(
        "compose",
        "-p",
        stack.project,
        "-f",
        str(stack.file),
        "exec",
        "-T",
        stack.target,
        "touch",
        "/tmp/down",
    )
    try:
        stack.until(
            lambda: stack.reported("/user/v1/ping") == "unavailable",
            "the outage answer",
        )
    finally:
        _docker(
            "compose",
            "-p",
            stack.project,
            "-f",
            str(stack.file),
            "exec",
            "-T",
            stack.target,
            "rm",
            "-f",
            "/tmp/down",
        )
    stack.healthy()


def test_maintenance_mode_takes_over_the_api_host_only_and_lifts_cleanly(
    stack: Stack,
) -> None:
    stack.compose("up", "-d", "--wait", "maintenance")
    try:
        stack.until(
            lambda: stack.get("/user/v1/ping").status_code == 503,
            "the maintenance answer",
        )
        answer = stack.get("/user/v1/ping", origin=ORIGIN)
        preflight = stack.get("/user/v1/ping", origin=ORIGIN, method="OPTIONS")
        stranger = stack.get("/user/v1/ping", origin="https://evil.example")
        assert answer.json()["status"] == "maintenance"
        assert answer.headers["retry-after"] == "120"
        assert answer.headers["access-control-allow-origin"] == ORIGIN
        assert answer.headers["access-control-allow-credentials"] == "true"
        assert preflight.status_code == 204
        assert preflight.headers["access-control-allow-headers"] == "authorization"
        assert "access-control-allow-origin" not in stranger.headers
        assert stack.status("/anything/at/all") == 503
        assert stack.status("/", host=WEB) == 200
    finally:
        stack.compose("rm", "-sf", "maintenance")
    stack.healthy()


def test_a_stopped_frontend_is_answered_with_the_outage_page(stack: Stack) -> None:
    stack.compose("stop", "frontend")
    try:
        stack.until(
            lambda: stack.get("/", host=WEB, accept="text/html").status_code == 503,
            "the outage page",
        )
        page = stack.get("/", host=WEB, accept="text/html")
        assert "text/html" in page.headers["content-type"]
        assert stack.status("/user/v1/ping") == 200
    finally:
        stack.compose("start", "frontend")
        stack.healthy()
