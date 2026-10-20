from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.schema.message.org import (
    GetOrganizationRequest,
    ResolveFacultyRequest,
    ResolveOrganizationRequest,
    ResolveUniversityRequest,
)
from org.api.kafka.sub.reference import (
    on_get_organization,
    on_resolve_faculty,
    on_resolve_organization,
    on_resolve_university,
)
from org.uow.reference import ReferenceUOW

Maker = async_sessionmaker[AsyncSession]


@pytest.fixture
def announced(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    events: list[Any] = []

    async def record(organizations: list[Any]) -> None:
        events.extend(organizations)

    monkeypatch.setattr("org.service.reference.on_organization_created", record)
    return events


async def test_a_university_is_found_by_its_name_or_made_once(
    org_sessionmaker: Maker, announced: list[Any]
) -> None:
    uow = ReferenceUOW(org_sessionmaker)

    made = await on_resolve_university(
        ResolveUniversityRequest(name="  МГУ  им. Ломоносова"), uow
    )
    found = await on_resolve_university(
        ResolveUniversityRequest(name="мгу им. ломоносова"),
        ReferenceUOW(org_sessionmaker),
    )

    assert made.error is None and found.error is None
    assert made.data is not None and found.data is not None
    assert (made.data.name, made.data.type) == ("МГУ им. Ломоносова", "university")
    assert found.data.id == made.data.id
    assert [(e.id, e.type) for e in announced] == [(made.data.id, "university")]


async def test_a_faculty_is_told_apart_by_its_university(
    org_sessionmaker: Maker, announced: list[Any]
) -> None:
    first = (
        await on_resolve_university(
            ResolveUniversityRequest(name="First"), ReferenceUOW(org_sessionmaker)
        )
    ).data
    second = (
        await on_resolve_university(
            ResolveUniversityRequest(name="Second"), ReferenceUOW(org_sessionmaker)
        )
    ).data
    assert first is not None and second is not None

    async def faculty(university: Any, name: str = "Law") -> Any:
        answer = await on_resolve_faculty(
            ResolveFacultyRequest(name=name, university_id=university.id),
            ReferenceUOW(org_sessionmaker),
        )
        assert answer.error is None
        return answer.data

    law, again, other = (
        await faculty(first),
        await faculty(first, "LAW"),
        await faculty(second),
    )

    assert again.id == law.id
    assert other.id != law.id
    assert law.type == "faculty"


async def test_a_faculty_needs_a_university_that_exists(
    org_sessionmaker: Maker, announced: list[Any]
) -> None:
    answer = await on_resolve_faculty(
        ResolveFacultyRequest(name="Law", university_id=uuid4()),
        ReferenceUOW(org_sessionmaker),
    )

    assert answer.data is None and answer.error is not None
    assert (answer.error.code, answer.error.detail) == (404, "UNIVERSITY_NOT_FOUND")
    assert announced == []


async def test_a_workplace_is_an_organization_or_a_university(
    org_sessionmaker: Maker, announced: list[Any]
) -> None:
    university = (
        await on_resolve_university(
            ResolveUniversityRequest(name="Polytech"), ReferenceUOW(org_sessionmaker)
        )
    ).data
    assert university is not None

    same = await on_resolve_organization(
        ResolveOrganizationRequest(name="polytech"), ReferenceUOW(org_sessionmaker)
    )
    company = await on_resolve_organization(
        ResolveOrganizationRequest(name="Acme"), ReferenceUOW(org_sessionmaker)
    )
    company_again = await on_resolve_organization(
        ResolveOrganizationRequest(name="ACME"), ReferenceUOW(org_sessionmaker)
    )

    assert same.data is not None and same.data.id == university.id
    assert company.data is not None and company.data.type == "organization"
    assert company_again.data is not None and company_again.data.id == company.data.id


async def test_an_organization_is_read_by_its_id(
    org_sessionmaker: Maker, announced: list[Any]
) -> None:
    made = (
        await on_resolve_university(
            ResolveUniversityRequest(name="Polytech"), ReferenceUOW(org_sessionmaker)
        )
    ).data
    assert made is not None

    found = await on_get_organization(
        GetOrganizationRequest(id=made.id), ReferenceUOW(org_sessionmaker)
    )
    missing = await on_get_organization(
        GetOrganizationRequest(id=uuid4()), ReferenceUOW(org_sessionmaker)
    )

    assert found.data is not None and found.data.id == made.id
    assert missing.error is not None
    assert (missing.error.code, missing.error.detail) == (404, "ORGANIZATION_NOT_FOUND")
