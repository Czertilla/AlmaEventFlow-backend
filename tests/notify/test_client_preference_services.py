from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.enum.notify import TransportTypeEnum
from notify.dto.client import ClientCreateDTO
from notify.dto.preference import (
    PreferenceItemDTO,
    PreferencesDTO,
    PreferencesUpdateDTO,
)
from notify.exc import (
    ClientNotExistsException,
    TransportNotSupportedException,
    WebPushClientInvalidException,
)
from notify.service.client import ClientService
from notify.service.preference import PreferenceService
from notify.transport import registry
from notify.uow.client import ClientUOW
from notify.uow.preference import PreferenceUOW

Maker = async_sessionmaker[AsyncSession]
SUBSCRIPTION = {"p256dh": "key", "auth": "secret"}


def _client(
    endpoint: str = "https://push.example/a",
    *,
    label: str | None = None,
    transport: TransportTypeEnum = TransportTypeEnum.webpush,
    payload: dict[str, str] | None = None,
) -> ClientCreateDTO:
    return ClientCreateDTO(
        endpoint=endpoint,
        transport=transport,
        label=label,
        payload=dict(SUBSCRIPTION) if payload is None else payload,
    )


async def test_client_registration_round_trip(sessionmaker_: Maker) -> None:
    user_id = uuid4()
    service = ClientService(ClientUOW(sessionmaker_))

    created = await service.register(user_id, _client(label="Laptop"))

    assert created.transport == TransportTypeEnum.webpush
    assert (created.endpoint, created.label, created.is_active) == (
        "https://push.example/a",
        "Laptop",
        True,
    )
    assert await service.list_my(user_id) == [created]
    assert await service.list_my(uuid4()) == []

    await service.delete(user_id, created.id)
    assert await service.list_my(user_id) == []


async def test_registering_the_same_endpoint_updates_the_client(
    sessionmaker_: Maker,
) -> None:
    user_id = uuid4()
    service = ClientService(ClientUOW(sessionmaker_))

    first = await service.register(user_id, _client(label="old"))
    again = await service.register(user_id, _client(label="new"))

    assert again.id == first.id
    assert again.label == "new"
    assert len(await service.list_my(user_id)) == 1


async def test_client_with_an_incomplete_webpush_payload_is_rejected(
    sessionmaker_: Maker,
) -> None:
    service = ClientService(ClientUOW(sessionmaker_))

    with pytest.raises(WebPushClientInvalidException):
        await service.register(uuid4(), _client(payload={"p256dh": "key"}))


async def test_client_for_an_unsupported_transport_is_rejected(
    sessionmaker_: Maker,
) -> None:
    unsupported = next((t for t in TransportTypeEnum if registry.get(t) is None), None)
    if unsupported is None:
        pytest.skip("every transport type is registered")
    service = ClientService(ClientUOW(sessionmaker_))

    with pytest.raises(TransportNotSupportedException):
        await service.register(uuid4(), _client(transport=unsupported))


async def test_deleting_somebody_elses_client_is_rejected(sessionmaker_: Maker) -> None:
    service = ClientService(ClientUOW(sessionmaker_))
    created = await service.register(uuid4(), _client())

    with pytest.raises(ClientNotExistsException):
        await service.delete(uuid4(), created.id)


def _enabled(preferences: PreferencesDTO) -> dict[TransportTypeEnum, bool]:
    return {item.transport: item.is_enabled for item in preferences.preferences}


async def test_preferences_default_to_the_registry(sessionmaker_: Maker) -> None:
    service = PreferenceService(PreferenceUOW(sessionmaker_))

    prefs = await service.get_my(uuid4())

    assert set(_enabled(prefs)) == {t.type for t in registry.all_transports()}
    assert _enabled(prefs)[registry.GUARANTEED] is True


async def test_preferences_replace_and_keep_the_guaranteed_transport_on(
    sessionmaker_: Maker,
) -> None:
    user_id = uuid4()
    service = PreferenceService(PreferenceUOW(sessionmaker_))

    saved = await service.set_my(
        user_id,
        PreferencesUpdateDTO(
            preferences=[
                PreferenceItemDTO(transport=registry.GUARANTEED, is_enabled=False),
                PreferenceItemDTO(
                    transport=TransportTypeEnum.webpush, is_enabled=False
                ),
            ]
        ),
    )

    assert _enabled(saved)[registry.GUARANTEED] is True
    assert _enabled(saved)[TransportTypeEnum.webpush] is False
    assert await service.get_my(user_id) == saved
