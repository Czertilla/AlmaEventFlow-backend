import logging
from pathlib import Path
from profile.utils.rsa import ensure_invite_keys

import pytest

from core.config.settings import settings
from core.utils.keys import KeyMissingError


@pytest.fixture
def paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    private_path, public_path = tmp_path / "private.pem", tmp_path / "public.pem"
    monkeypatch.setattr(settings, "PROFILE_RSA_PRIVATE_KEY_PATH", str(private_path))
    monkeypatch.setattr(settings, "PROFILE_RSA_PUBLIC_KEY_PATH", str(public_path))
    return private_path, public_path


def test_the_monolith_makes_the_pair_when_there_is_none(
    monkeypatch: pytest.MonkeyPatch, paths: tuple[Path, Path]
) -> None:
    private_path, public_path = paths
    monkeypatch.setattr(settings, "MONOLITH", True)

    ensure_invite_keys()

    assert "PRIVATE KEY" in private_path.read_text()
    assert "PUBLIC KEY" in public_path.read_text()
    assert "PRIVATE" not in public_path.read_text()


def test_a_pair_that_is_there_is_left_alone(
    monkeypatch: pytest.MonkeyPatch, paths: tuple[Path, Path]
) -> None:
    private_path, public_path = paths
    private_path.write_text("private")
    public_path.write_text("public")
    monkeypatch.setattr(settings, "MONOLITH", True)

    ensure_invite_keys()

    assert (private_path.read_text(), public_path.read_text()) == ("private", "public")


@pytest.mark.parametrize("monolith", [True, False])
def test_half_a_pair_stops_the_start(
    monkeypatch: pytest.MonkeyPatch, paths: tuple[Path, Path], monolith: bool
) -> None:
    paths[1].write_text("public")
    monkeypatch.setattr(settings, "MONOLITH", monolith)

    with pytest.raises(KeyMissingError):
        ensure_invite_keys()


def test_outside_the_monolith_nothing_is_made_and_the_start_stops(
    monkeypatch: pytest.MonkeyPatch,
    paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(settings, "MONOLITH", False)

    with caplog.at_level(logging.CRITICAL), pytest.raises(KeyMissingError):
        ensure_invite_keys()

    assert not paths[0].exists() and not paths[1].exists()
    assert any(r.levelno == logging.CRITICAL for r in caplog.records)
