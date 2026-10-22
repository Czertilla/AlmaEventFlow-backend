import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from support.http import AsPerson, principal

from core.config.settings import settings
from core.utils.invite import decode_invite_token

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN = principal(superuser=True)


async def _person(api: httpx.AsyncClient) -> UUID:
    response = await api.post(
        f"{V1}/persons", json={"surname": "Ivanov", "name": "Ivan"}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return UUID(response.json()["id"])


async def test_an_invite_names_the_person_it_was_issued_for(
    api: httpx.AsyncClient,
) -> None:
    person_id = await _person(api)

    default = await api.post(f"{V2}/persons/{person_id}/invite", json={}, headers=ADMIN)
    short = await api.post(
        f"{V2}/persons/{person_id}/invite", json={"expires_in": 60}, headers=ADMIN
    )

    assert default.status_code == short.status_code == 200, default.text
    assert decode_invite_token(default.json()["token"]) == person_id
    assert decode_invite_token(short.json()["token"]) == person_id
    assert default.json()["expires_at"] > short.json()["expires_at"] > time.time()


async def test_an_invite_is_not_issued_for_an_unknown_person(
    api: httpx.AsyncClient,
) -> None:
    response = await api.post(
        f"{V2}/persons/{uuid4()}/invite", json={}, headers=ADMIN
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PERSON_NOT_FOUND"


async def test_an_invite_is_not_issued_for_a_person_who_has_an_account(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    person_id = await _person(api)
    await as_person(person_id)

    response = await api.post(
        f"{V2}/persons/{person_id}/invite", json={}, headers=ADMIN
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "PERSON_ALREADY_HAS_ACCOUNT"


async def test_an_invite_is_for_superusers_only(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)
    url = f"{V2}/persons/{person_id}/invite"

    ordinary = await api.post(url, json={}, headers=principal())
    anonymous = await api.post(url, json={})

    assert ordinary.status_code == 403
    assert anonymous.status_code in (401, 403)


async def test_an_invite_lives_for_a_positive_time(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)

    response = await api.post(
        f"{V2}/persons/{person_id}/invite", json={"expires_in": 0}, headers=ADMIN
    )

    assert response.status_code == 422


def _files(folder: Path) -> list[Path]:
    return list(folder.iterdir())


async def test_an_invite_cannot_be_signed_when_the_private_key_is_gone(
    api: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    person_id = await _person(api)
    monkeypatch.setattr(
        settings, "PROFILE_RSA_PRIVATE_KEY_PATH", str(tmp_path / "private.pem")
    )
    monkeypatch.setattr(
        settings, "PROFILE_RSA_PUBLIC_KEY_PATH", str(tmp_path / "public.pem")
    )

    response = await api.post(
        f"{V2}/persons/{person_id}/invite", json={}, headers=ADMIN
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "INVITE_SIGNING_NOT_CONFIGURED"
    assert _files(tmp_path) == []
