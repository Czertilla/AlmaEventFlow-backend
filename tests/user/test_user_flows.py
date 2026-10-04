import hashlib
import hmac
import time
from uuid import UUID, uuid4

import httpx
import pytest
from _outbox import Outbox
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

PASSWORD = "S3cret-pass"
NEW_PASSWORD = "An0ther-pass"
BOT_TOKEN = "123456:TEST-TOKEN"
JWT_PREFIX = "/user/v1/auth/jwt"
VERIFY_PAGE = "/user/v1/auth/v1/verify/email"
Maker = async_sessionmaker[AsyncSession]


async def _register(
    client: httpx.AsyncClient,
    email: str = "ann@example.com",
    username: str = "ann",
    **extra: object,
) -> httpx.Response:
    return await client.post(
        "/user/v1/auth/register",
        json={"email": email, "password": PASSWORD, "username": username, **extra},
    )


async def _login(
    client: httpx.AsyncClient,
    email: str = "ann@example.com",
    password: str = PASSWORD,
) -> httpx.Response:
    return await client.post(
        f"{JWT_PREFIX}/login", data={"username": email, "password": password}
    )


def _bearer(response: httpx.Response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _sql(engine: AsyncEngine, statement: str, **params: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement), params)


async def _verified_session(
    client: httpx.AsyncClient,
    engine: AsyncEngine,
    email: str = "ann@example.com",
    username: str = "ann",
    *,
    superuser: bool = False,
) -> dict[str, str]:
    await _register(client, email, username)
    await _sql(
        engine,
        'UPDATE "user" SET is_verified = true, is_superuser = :su WHERE email = :email',
        su=superuser,
        email=email,
    )
    return _bearer(await _login(client, email))


def _configure(monkeypatch: pytest.MonkeyPatch, name: str, value: object) -> None:
    from core.config.settings import settings as core_settings
    from user.config.settings import settings as user_settings

    for target in (core_settings, user_settings):
        monkeypatch.setattr(target, name, value)


async def _person(engine: AsyncEngine) -> UUID:
    person_id = uuid4()
    await _sql(engine, "INSERT INTO person (id) VALUES (:id)", id=person_id)
    return person_id


async def test_register_creates_the_account_and_announces_it(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    response = await _register(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "ann@example.com"
    assert body["username"] == "ann"
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert body["is_superuser"] is False
    assert body["person_id"] is None
    assert "password" not in body and "hashed_password" not in body
    assert outbox.count("created") == 1
    assert outbox.last("created")[:3] == (UUID(body["id"]), "ann@example.com", False)


async def test_register_ignores_privileged_fields(
    client: httpx.AsyncClient,
) -> None:
    response = await _register(client, is_superuser=True, is_verified=True)

    assert response.status_code == 201, response.text
    assert response.json()["is_superuser"] is False
    assert response.json()["is_verified"] is False


async def test_register_rejects_duplicates(client: httpx.AsyncClient) -> None:
    await _register(client)

    same_email = await _register(client, username="other")
    same_username = await _register(client, email="other@example.com")

    assert same_email.status_code == 400
    assert same_email.json()["detail"] == "REGISTER_USER_ALREADY_EXISTS"
    assert same_username.status_code == 400
    assert same_username.json()["detail"] == "USERNAME_ALREADY_EXISTS"


async def test_login_issues_a_token_and_the_session_cookies(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    registered = (await _register(client)).json()

    response = await _login(client)

    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    assert client.cookies.get("refresh")
    assert client.cookies.get("session")
    assert len(outbox.notifications) == 1
    assert outbox.notifications[0].user_ids == [UUID(registered["id"])]


async def test_login_rejects_bad_credentials(client: httpx.AsyncClient) -> None:
    await _register(client)

    wrong_password = await _login(client, password="nope")
    unknown_user = await _login(client, email="ghost@example.com")

    for response in (wrong_password, unknown_user):
        assert response.status_code == 400
        assert response.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


async def test_login_rejects_an_inactive_account(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    await _register(client)
    await _sql(user_engine, 'UPDATE "user" SET is_active = false')

    response = await _login(client)

    assert response.status_code == 400
    assert response.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


async def test_me_requires_a_verified_account_until_the_email_is_verified(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    await _register(client)
    headers = _bearer(await _login(client))

    before = await client.get("/user/v1/users/me", headers=headers)
    requested = await client.post(
        "/user/v1/auth/request-verify-token", json={"email": "ann@example.com"}
    )
    email, token = outbox.verify[-1]
    verified = await client.get(VERIFY_PAGE, params={"token": token})
    after = await client.get("/user/v1/users/me", headers=_bearer(await _login(client)))

    assert before.status_code == 403
    assert requested.status_code == 202
    assert email == "ann@example.com"
    assert verified.status_code == 200
    assert outbox.count("verified") == 1
    assert after.status_code == 200, after.text
    assert after.json()["is_verified"] is True
    again = await client.get(VERIFY_PAGE, params={"token": token})
    assert again.status_code == 200
    assert outbox.count("verified") == 1


async def test_verify_endpoint_rejects_a_garbage_token(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/user/v1/auth/verify", json={"token": "garbage"})

    assert response.status_code == 400
    assert response.json()["detail"] == "VERIFY_USER_BAD_TOKEN"


async def test_request_verify_token_for_a_verified_account_is_ignored(
    client: httpx.AsyncClient, user_engine: AsyncEngine, outbox: Outbox
) -> None:
    await _verified_session(client, user_engine)

    response = await client.post(
        "/user/v1/auth/request-verify-token", json={"email": "ann@example.com"}
    )

    assert response.status_code == 202
    assert outbox.verify == []


async def test_patch_me_changes_the_username_and_validates_it(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _verified_session(client, user_engine)
    await _register(client, "bob@example.com", "bob")

    renamed = await client.patch(
        "/user/v1/users/me", json={"username": "annie"}, headers=headers
    )
    taken = await client.patch(
        "/user/v1/users/me", json={"username": "bob"}, headers=headers
    )

    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["username"] == "annie"
    assert taken.status_code == 400
    assert taken.json()["detail"] == "USERNAME_ALREADY_EXISTS"


async def test_changing_the_password_needs_the_current_one(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _verified_session(client, user_engine)

    missing = await client.patch(
        "/user/v1/users/me",
        json={"username": "ann", "password": NEW_PASSWORD},
        headers=headers,
    )
    wrong = await client.patch(
        "/user/v1/users/me",
        json={
            "username": "ann",
            "password": NEW_PASSWORD,
            "current_password": "nope",
        },
        headers=headers,
    )
    changed = await client.patch(
        "/user/v1/users/me",
        json={
            "username": "ann",
            "password": NEW_PASSWORD,
            "current_password": PASSWORD,
        },
        headers=headers,
    )

    assert missing.status_code == 400
    assert missing.json()["detail"] == "INVALID_CURRENT_PASSWORD"
    assert wrong.status_code == 400
    assert changed.status_code == 200, changed.text
    assert (await _login(client, password=PASSWORD)).status_code == 400
    assert (await _login(client, password=NEW_PASSWORD)).status_code == 200


async def test_changing_the_email_resets_verification_and_announces_it(
    client: httpx.AsyncClient, user_engine: AsyncEngine, outbox: Outbox
) -> None:
    headers = await _verified_session(client, user_engine)

    response = await client.patch(
        "/user/v1/users/me",
        json={"username": "ann", "email": "new@example.com"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "new@example.com"
    assert response.json()["is_verified"] is False
    assert outbox.last("updated")[1:3] == ("new@example.com", False)


async def test_changing_to_a_taken_email_is_rejected(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _verified_session(client, user_engine)
    await _register(client, "bob@example.com", "bob")

    response = await client.patch(
        "/user/v1/users/me",
        json={"username": "ann", "email": "bob@example.com"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "UPDATE_USER_EMAIL_ALREADY_EXISTS"


async def test_forgot_and_reset_password_round_trip(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    await _register(client)

    forgot = await client.post(
        "/user/v1/auth/forgot-password", json={"email": "ann@example.com"}
    )
    email, token = outbox.reset[-1]
    reset = await client.post(
        "/user/v1/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD},
    )
    bad = await client.post(
        "/user/v1/auth/reset-password",
        json={"token": "garbage", "password": NEW_PASSWORD},
    )

    assert forgot.status_code == 202
    assert email == "ann@example.com"
    assert reset.status_code == 200, reset.text
    assert bad.status_code == 400
    assert bad.json()["detail"] == "RESET_PASSWORD_BAD_TOKEN"
    assert (await _login(client, password=PASSWORD)).status_code == 400
    assert (await _login(client, password=NEW_PASSWORD)).status_code == 200


async def test_forgot_password_for_an_unknown_email_stays_silent(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    response = await client.post(
        "/user/v1/auth/forgot-password", json={"email": "ghost@example.com"}
    )

    assert response.status_code == 202
    assert outbox.reset == []


async def test_resetting_the_password_revokes_the_refresh_tokens(
    client: httpx.AsyncClient, outbox: Outbox
) -> None:
    await _register(client)
    await _login(client)
    await client.post(
        "/user/v1/auth/forgot-password", json={"email": "ann@example.com"}
    )
    _, token = outbox.reset[-1]

    await client.post(
        "/user/v1/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD},
    )
    refreshed = await client.post(f"{JWT_PREFIX}/refresh")

    assert refreshed.status_code == 401
    assert refreshed.json()["detail"] == "INVALID_REFRESH_TOKEN"


async def test_refresh_rotates_the_token_and_detects_reuse(
    client: httpx.AsyncClient,
) -> None:
    await _register(client)
    await _login(client)
    first_refresh = client.cookies.get("refresh")
    assert first_refresh is not None

    refreshed = await client.post(f"{JWT_PREFIX}/refresh")
    second_refresh = client.cookies.get("refresh")
    client.cookies.set("refresh", first_refresh, path=f"{JWT_PREFIX}/refresh")
    replay = await client.post(f"{JWT_PREFIX}/refresh")

    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["token_type"] == "bearer"
    assert second_refresh != first_refresh
    assert replay.status_code == 401
    assert replay.json()["detail"] == "INVALID_REFRESH_TOKEN"


async def test_refresh_without_a_cookie_is_rejected(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(f"{JWT_PREFIX}/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "REFRESH_TOKEN_MISSING"


async def test_logout_revokes_the_refresh_token(client: httpx.AsyncClient) -> None:
    await _register(client)
    await _login(client)

    logout = await client.post(f"{JWT_PREFIX}/logout")
    refreshed = await client.post(f"{JWT_PREFIX}/refresh")

    assert logout.status_code == 204
    assert refreshed.status_code == 401


async def test_sessions_are_listed_and_revoked(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    await _register(client)
    await _sql(user_engine, 'UPDATE "user" SET is_verified = true')
    headers = _bearer(await _login(client))
    from user.app.app import app

    other = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    )
    async with other:
        await _login(other)

    listed = await client.get("/user/v1/users/me/sessions", headers=headers)
    items = listed.json()
    own = next(item for item in items if item["is_current"])
    foreign = next(item for item in items if not item["is_current"])
    missing = await client.delete(
        f"/user/v1/users/me/sessions/{uuid4()}", headers=headers
    )
    revoked = await client.delete(
        f"/user/v1/users/me/sessions/{foreign['id']}", headers=headers
    )
    after = await client.get("/user/v1/users/me/sessions", headers=headers)
    cleared = await client.delete("/user/v1/users/me/sessions", headers=headers)

    assert listed.status_code == 200
    assert len(items) == 2
    assert items[0]["is_current"] is True
    assert own["id"] != foreign["id"]
    assert missing.status_code == 404
    assert missing.json()["detail"] == "SESSION_NOT_FOUND"
    assert revoked.status_code == 204
    assert [item["id"] for item in after.json()] == [own["id"]]
    assert cleared.status_code == 204


async def test_check_username_reports_existence(
    client: httpx.AsyncClient,
) -> None:
    await _register(client)

    taken = await client.get("/user/v1/users/check/ann")
    free = await client.get("/user/v1/users/check/zed")

    assert taken.json() == {"username": "ann", "exists": True}
    assert free.json() == {"username": "zed", "exists": False}


async def test_users_are_searched_with_pagination(
    client: httpx.AsyncClient,
) -> None:
    await _register(client, "ann@example.com", "ann")
    await _register(client, "bob@example.com", "bob")

    everyone = await client.get("/user/v1/users", params={"limit": 1})
    found = await client.get("/user/v1/users", params={"search": "bob"})

    assert everyone.status_code == 200, everyone.text
    assert everyone.json()["pagination"]["total"] == 2
    assert len(everyone.json()["items"]) == 1
    assert [u["username"] for u in found.json()["items"]] == ["bob"]


async def test_the_users_router_reads_and_edits_any_account_as_a_superuser(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)
    bob = (await _register(client, "bob@example.com", "bob")).json()

    read = await client.get(f"/user/v1/users/{bob['id']}", headers=admin)
    patched = await client.patch(
        f"/user/v1/users/{bob['id']}",
        json={"is_verified": True, "username": "robert"},
        headers=admin,
    )
    missing = await client.get(f"/user/v1/users/{uuid4()}", headers=admin)
    deleted = await client.delete(f"/user/v1/users/{bob['id']}", headers=admin)

    assert read.status_code == 200
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_verified"] is True
    assert patched.json()["username"] == "robert"
    assert missing.status_code == 404
    assert deleted.status_code == 204


async def test_deleting_an_account_announces_it(
    client: httpx.AsyncClient, user_engine: AsyncEngine, outbox: Outbox
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)
    bob = (await _register(client, "bob@example.com", "bob")).json()

    await client.delete(f"/user/v1/users/{bob['id']}", headers=admin)

    assert outbox.last("deleted") == (UUID(bob["id"]),)
    assert (
        await client.get(f"/user/v1/users/{bob['id']}", headers=admin)
    ).status_code == 404


async def test_invite_token_links_a_person_at_registration(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)
    person_id = await _person(user_engine)

    invite = await client.post(
        "/user/v1/users/invite", json={"person_id": str(person_id)}, headers=admin
    )
    registered = await _register(
        client, "bob@example.com", "bob", invite_token=invite.json()["token"]
    )
    again = await client.post(
        "/user/v1/users/invite", json={"person_id": str(person_id)}, headers=admin
    )

    assert invite.status_code == 200, invite.text
    assert invite.json()["expires_at"] > time.time()
    assert registered.status_code == 201, registered.text
    assert registered.json()["person_id"] == str(person_id)
    assert again.status_code == 400
    assert again.json()["detail"] == "PERSON_ALREADY_HAS_ACCOUNT"


async def test_invite_for_an_unknown_person_is_rejected(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)

    response = await client.post(
        "/user/v1/users/invite", json={"person_id": str(uuid4())}, headers=admin
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "INVITE_PERSON_NOT_FOUND"


async def test_invite_endpoint_is_for_superusers_only(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _verified_session(client, user_engine)

    response = await client.post(
        "/user/v1/users/invite", json={"person_id": str(uuid4())}, headers=headers
    )

    assert response.status_code == 403


async def test_registering_with_a_bad_invite_token_is_rejected(
    client: httpx.AsyncClient,
) -> None:
    response = await _register(client, invite_token="garbage")

    assert response.status_code == 400
    assert response.json()["detail"] == "INVITE_TOKEN_INVALID"


async def test_link_invite_attaches_the_person_to_the_caller(
    client: httpx.AsyncClient, user_engine: AsyncEngine, outbox: Outbox
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)
    person_id = await _person(user_engine)
    token = (
        await client.post(
            "/user/v1/users/invite",
            json={"person_id": str(person_id)},
            headers=admin,
        )
    ).json()["token"]
    await _register(client, "bob@example.com", "bob")
    bob = _bearer(await _login(client, "bob@example.com"))

    linked = await client.post(
        "/user/v1/users/me/link-invite", json={"token": token}, headers=bob
    )
    twice = await client.post(
        "/user/v1/users/me/link-invite", json={"token": token}, headers=bob
    )

    assert linked.status_code == 200, linked.text
    assert linked.json()["person_id"] == str(person_id)
    assert outbox.last("updated")[3] == person_id
    assert twice.status_code == 400
    assert twice.json()["detail"] == "ACCOUNT_ALREADY_LINKED"


async def test_admin_links_a_person_to_an_account(
    client: httpx.AsyncClient, user_engine: AsyncEngine, outbox: Outbox
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)
    bob = (await _register(client, "bob@example.com", "bob")).json()
    person_id = await _person(user_engine)

    linked = await client.patch(
        f"/user/v1/users/{bob['id']}/person",
        json={"person_id": str(person_id)},
        headers=admin,
    )
    taken = await client.patch(
        f"/user/v1/users/{bob['id']}/person",
        json={"person_id": str(person_id)},
        headers=admin,
    )
    unknown_user = await client.patch(
        f"/user/v1/users/{uuid4()}/person",
        json={"person_id": str(person_id)},
        headers=admin,
    )
    unknown_person = await client.patch(
        f"/user/v1/users/{bob['id']}/person",
        json={"person_id": str(uuid4())},
        headers=admin,
    )

    assert linked.status_code == 200, linked.text
    assert linked.json()["person_id"] == str(person_id)
    assert outbox.last("updated")[3] == person_id
    assert taken.status_code == 400
    assert taken.json()["detail"] == "PERSON_ALREADY_HAS_ACCOUNT"
    assert unknown_user.status_code == 404
    assert unknown_user.json()["detail"] == "USER_NOT_FOUND"
    assert unknown_person.status_code == 400
    assert unknown_person.json()["detail"] == "INVITE_PERSON_NOT_FOUND"


async def test_telegram_link_token_needs_a_person_and_a_configured_bot(
    client: httpx.AsyncClient,
    user_engine: AsyncEngine,
    outbox: Outbox,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = await _verified_session(client, user_engine, superuser=True)
    bob = (await _register(client, "bob@example.com", "bob")).json()
    person_id = await _person(user_engine)
    await client.patch(
        f"/user/v1/users/{bob['id']}/person",
        json={"person_id": str(person_id)},
        headers=admin,
    )
    await _sql(
        user_engine, "UPDATE \"user\" SET is_verified = true WHERE username = 'bob'"
    )
    bob_headers = _bearer(await _login(client, "bob@example.com"))
    no_person = await client.post(
        "/user/v1/users/me/telegram/link-token", headers=admin
    )
    _configure(monkeypatch, "BOT_TG_USERNAME", None)
    unconfigured = await client.post(
        "/user/v1/users/me/telegram/link-token", headers=bob_headers
    )
    _configure(monkeypatch, "BOT_TG_USERNAME", "aef_bot")

    issued = await client.post(
        "/user/v1/users/me/telegram/link-token", headers=bob_headers
    )

    assert no_person.status_code == 400
    assert no_person.json()["detail"] == "TELEGRAM_LINK_PERSON_REQUIRED"
    assert unconfigured.status_code == 503
    assert issued.status_code == 200, issued.text
    body = issued.json()
    assert body["deep_link"] == f"https://t.me/aef_bot?start={body['token']}"
    assert outbox.last("telegram_link_code")[:2] == (body["token"], person_id)


def _widget_payload(telegram_id: int, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": telegram_id,
        "first_name": "Bob",
        "auth_date": int(time.time()),
    } | overrides
    check = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items()) if value is not None
    )
    key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    data["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    return data


async def test_telegram_widget_login_requires_a_linked_account(
    client: httpx.AsyncClient,
    user_engine: AsyncEngine,
    user_sessionmaker: Maker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.schema.message.user import (
        LinkTelegramOAuthRequest,
        UnlinkTelegramOAuthRequest,
    )
    from user.api.kafka.sub.telegram import (
        on_link_telegram_oauth,
        on_unlink_telegram_oauth,
    )
    from user.uow.user import UserUOW

    _configure(monkeypatch, "BOT_TG_TOKEN", BOT_TOKEN)
    await _register(client, "bob@example.com", "bob")
    person_id = await _person(user_engine)
    await _sql(
        user_engine,
        "UPDATE \"user\" SET person_id = :person WHERE username = 'bob'",
        person=person_id,
    )
    uow = UserUOW(user_sessionmaker)

    unlinked = await client.post(
        "/user/v1/auth/telegram/login", json=_widget_payload(777)
    )
    forged = await client.post(
        "/user/v1/auth/telegram/login",
        json=_widget_payload(777) | {"hash": "0" * 64},
    )
    await on_link_telegram_oauth(
        LinkTelegramOAuthRequest(
            person_id=person_id, telegram_id="777", username="bobby"
        ),
        uow,
    )
    linked = await client.post(
        "/user/v1/auth/telegram/login", json=_widget_payload(777)
    )
    await on_unlink_telegram_oauth(UnlinkTelegramOAuthRequest(person_id=person_id), uow)
    unlinked_again = await client.post(
        "/user/v1/auth/telegram/login", json=_widget_payload(777)
    )

    assert unlinked.status_code == 404
    assert unlinked.json()["detail"] == "TELEGRAM_ACCOUNT_NOT_LINKED"
    assert forged.status_code == 400
    assert forged.json()["detail"] == "TELEGRAM_AUTH_INVALID"
    assert linked.status_code == 200, linked.text
    assert linked.json()["token_type"] == "bearer"
    assert unlinked_again.status_code == 404


async def _count(engine: AsyncEngine, table: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


@pytest.fixture
def google(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    from httpx_oauth.oauth2 import OAuth2Token

    from user.api.oauth2 import google_oauth_client

    profile: dict[str, object] = {
        "id": "g-1",
        "email": "gina@example.com",
        "name": "gina",
    }

    async def get_access_token(*_: object, **__: object) -> OAuth2Token:
        return OAuth2Token(
            {
                "access_token": "google-token",
                "expires_at": int(time.time()) + 3600,
                "refresh_token": "google-refresh",
            }
        )

    async def get_id_email(_: str) -> tuple[object, tuple[object, object]]:
        return profile["id"], (profile["email"], profile["name"])

    monkeypatch.setattr(google_oauth_client, "get_access_token", get_access_token)
    monkeypatch.setattr(google_oauth_client, "get_id_email", get_id_email)
    return profile


def _oauth_state(client: httpx.AsyncClient, subject: str | None = None) -> str:
    from fastapi_users.router.oauth import (
        CSRF_TOKEN_COOKIE_NAME,
        CSRF_TOKEN_KEY,
        generate_state_token,
    )

    from user.config.settings import settings

    client.cookies.set(CSRF_TOKEN_COOKIE_NAME, "csrf-token")
    data = {CSRF_TOKEN_KEY: "csrf-token"}
    if subject is not None:
        data["sub"] = subject
    return generate_state_token(data, settings.OAUTH_STATE_SECRET.get_secret_value())


async def test_google_callback_creates_a_verified_account_once(
    client: httpx.AsyncClient,
    user_engine: AsyncEngine,
    outbox: Outbox,
    google: dict[str, object],
) -> None:
    first = await client.get(
        "/user/v1/auth/google/callback",
        params={"code": "c", "state": _oauth_state(client)},
    )
    second = await client.get(
        "/user/v1/auth/google/callback",
        params={"code": "c", "state": _oauth_state(client)},
    )

    assert first.status_code == 200, first.text
    assert first.json()["token_type"] == "bearer"
    assert client.cookies.get("refresh")
    assert second.status_code == 200, second.text
    assert await _count(user_engine, '"user"') == 1
    assert await _count(user_engine, "oauth_account") == 1
    assert outbox.count("created") == 1
    assert outbox.last("created")[1:3] == ("gina@example.com", True)


async def test_google_callback_attaches_to_an_account_with_the_same_email(
    client: httpx.AsyncClient,
    user_engine: AsyncEngine,
    google: dict[str, object],
) -> None:
    await _register(client, "gina@example.com", "gina")

    response = await client.get(
        "/user/v1/auth/google/callback",
        params={"code": "c", "state": _oauth_state(client)},
    )

    assert response.status_code == 200, response.text
    assert await _count(user_engine, '"user"') == 1
    assert await _count(user_engine, "oauth_account") == 1


async def test_google_callback_rejects_a_forged_state(
    client: httpx.AsyncClient, google: dict[str, object]
) -> None:
    from fastapi_users.router.oauth import generate_state_token

    response = await client.get(
        "/user/v1/auth/google/callback",
        params={"code": "c", "state": generate_state_token({}, "SECRET")},
    )

    assert response.status_code == 400


async def test_associate_callback_adds_a_google_account_to_the_caller(
    client: httpx.AsyncClient,
    user_engine: AsyncEngine,
    google: dict[str, object],
) -> None:
    headers = await _verified_session(client, user_engine)
    me = (await client.get("/user/v1/users/me", headers=headers)).json()

    response = await client.get(
        "/user/v1/auth/associate/google/callback",
        params={"code": "c", "state": _oauth_state(client, me["id"])},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == me["id"]
    assert await _count(user_engine, "oauth_account") == 1
    assert await _count(user_engine, '"user"') == 1
