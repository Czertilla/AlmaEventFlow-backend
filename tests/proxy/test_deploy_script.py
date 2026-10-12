import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
NGINX_IMAGE = os.environ.get("PROXY_TEST_NGINX_IMAGE", "nginx:1.27-alpine")
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
ALL_PROFILES = "monolith,microservices,maintenance"
INFRA = {"pg", "status-page"}


def _bash() -> str | None:
    if os.environ.get("DEPLOY_TEST_BASH"):
        return os.environ["DEPLOY_TEST_BASH"]
    if os.name == "nt":
        return str(GIT_BASH) if GIT_BASH.exists() else None
    return shutil.which("bash")


def _service(*profiles: str, **extra: object) -> dict[str, object]:
    spec: dict[str, object] = {
        "image": NGINX_IMAGE,
        "healthcheck": {
            "test": ["CMD-SHELL", "exit 0"],
            "interval": "1s",
            "timeout": "2s",
            "retries": 3,
        },
        **extra,
    }
    if profiles:
        spec["profiles"] = list(profiles)
    return spec


class Deploy:
    def __init__(self, tmp: Path, bash: str) -> None:
        self.bash = bash
        self.project = f"aefdeploy{uuid.uuid4().hex[:8]}"
        self.file = tmp / "docker-compose.yml"
        broken = {
            "test": ["CMD-SHELL", "[ '${USER_HEALTH:-ok}' = ok ]"],
            "interval": "1s",
            "timeout": "2s",
            "retries": 2,
        }
        services = {
            "pg": _service(),
            "status-page": _service(),
            "aef": _service(
                "monolith", build={"context": ".", "dockerfile": "Dockerfile.missing"}
            ),
            "user": _service("microservices", healthcheck=broken),
            "notify": _service("microservices"),
            "bot": _service("monolith", "microservices"),
            "maintenance": _service("maintenance"),
        }
        self.file.write_text(yaml.safe_dump({"services": services}), encoding="utf-8")

    def env(self, **extra: str) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k != "COMPOSE_PROFILES"}
        env.update(
            COMPOSE_FILE=str(self.file),
            COMPOSE_PROJECT_NAME=self.project,
            SETTLE="0",
            WAIT_TIMEOUT="60",
        )
        env.update(extra)
        return env

    def run(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.bash, "scripts/deploy.sh", *args],
            cwd=ROOT,
            env=self.env(**env),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            check=False,
        )

    def running(self) -> set[str]:
        out = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
                "--format",
                '{{.Label "com.docker.compose.service"}}',
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return set(out.stdout.split())

    def teardown(self) -> None:
        subprocess.run(
            ["docker", "compose", "down", "-v", "--remove-orphans"],
            env=self.env(COMPOSE_PROFILES=ALL_PROFILES),
            capture_output=True,
            check=False,
        )


@pytest.fixture(scope="module")
def deploy(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Deploy]:
    if (
        subprocess.run(["docker", "info"], capture_output=True, check=False).returncode
        != 0
    ):
        pytest.skip("docker is not available")
    if (
        subprocess.run(
            ["docker", "image", "inspect", NGINX_IMAGE],
            capture_output=True,
            check=False,
        ).returncode
        != 0
    ):
        pytest.skip(
            f"image {NGINX_IMAGE!r} is not available locally "
            "(set PROXY_TEST_NGINX_IMAGE)"
        )
    bash = _bash()
    if bash is None:
        pytest.skip("bash is not available (set DEPLOY_TEST_BASH)")
    built = Deploy(tmp_path_factory.mktemp("deploy"), bash)
    try:
        yield built
    finally:
        built.teardown()


def test_the_monolith_is_deployed_with_the_maintenance_mode_lifted_afterwards(
    deploy: Deploy,
) -> None:
    result = deploy.run("--mode", "monolith", "--no-build")

    assert result.returncode == 0, result.stderr
    assert deploy.running() == {*INFRA, "aef", "bot"}


def test_switching_to_microservices_removes_the_monolith_and_keeps_the_shared_bot(
    deploy: Deploy,
) -> None:
    result = deploy.run("--mode", "microservices", "--no-build")

    assert result.returncode == 0, result.stderr
    assert deploy.running() == {*INFRA, "user", "notify", "bot"}
    assert (
        "aef"
        not in subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"label=com.docker.compose.project={deploy.project}",
                "--format",
                '{{.Label "com.docker.compose.service"}}',
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    )


def test_the_mode_comes_from_compose_profiles_when_no_flag_is_given(
    deploy: Deploy,
) -> None:
    result = deploy.run("--no-build", COMPOSE_PROFILES="monolith")

    assert result.returncode == 0, result.stderr
    assert deploy.running() == {*INFRA, "aef", "bot"}


@pytest.mark.parametrize(
    ("profiles", "complaint"),
    [("", "режим не выбран"), ("monolith,microservices", "и монолит, и микросервисы")],
)
def test_an_unclear_mode_is_refused_and_nothing_changes(
    deploy: Deploy, profiles: str, complaint: str
) -> None:
    before = deploy.running()

    result = deploy.run("--no-build", COMPOSE_PROFILES=profiles)

    assert result.returncode != 0
    assert complaint in result.stderr
    assert deploy.running() == before


def test_the_maintenance_commands_switch_the_mode_and_report_it(deploy: Deploy) -> None:
    on = deploy.run("maintenance", "on")
    state_on = deploy.run("maintenance", "status")
    during = deploy.running()
    off = deploy.run("maintenance", "off")
    state_off = deploy.run("maintenance", "status")

    assert (on.returncode, off.returncode) == (0, 0), (on.stderr, off.stderr)
    assert "maintenance" in during
    assert (state_on.stdout.strip(), state_off.stdout.strip()) == ("on", "off")
    assert "maintenance" not in deploy.running()


def test_keep_maintenance_leaves_the_mode_on_after_a_successful_deploy(
    deploy: Deploy,
) -> None:
    result = deploy.run("--mode", "monolith", "--no-build", "--keep-maintenance")

    assert result.returncode == 0, result.stderr
    assert "maintenance" in deploy.running()
    assert deploy.run("maintenance", "off").returncode == 0


def test_a_failed_deploy_keeps_the_maintenance_mode_on_and_says_how_to_lift_it(
    deploy: Deploy,
) -> None:
    result = deploy.run("--mode", "microservices", "--no-build", USER_HEALTH="broken")

    assert result.returncode != 0
    assert "maintenance" in deploy.running()
    assert "ВКЛЮЧЁН" in result.stderr
    assert "maintenance off" in result.stderr
    assert deploy.run("maintenance", "off").returncode == 0
    assert "maintenance" not in deploy.running()


def test_a_failed_build_changes_nothing_and_never_starts_the_maintenance_mode(
    deploy: Deploy,
) -> None:
    before = deploy.running()

    result = deploy.run("--mode", "monolith")

    assert result.returncode != 0
    assert "сборка не удалась" in result.stderr
    assert deploy.running() == before
