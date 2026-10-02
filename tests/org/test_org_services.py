from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.dto.pagination import PageParamDTO
from org.dto.collective import (
    CollectiveCreateDTO,
    CollectiveFilterDTO,
    CollectivePatchDTO,
    CollectivePutDTO,
)
from org.dto.faculty import (
    FacultyCreateDTO,
    FacultyFilterDTO,
    FacultyPatchDTO,
    FacultyPutDTO,
)
from org.dto.organization import (
    OrganizationCreateDTO,
    OrganizationFilterDTO,
    OrganizationPatchDTO,
    OrganizationPutDTO,
)
from org.dto.university import (
    UniversityCreateDTO,
    UniversityFilterDTO,
    UniversityPatchDTO,
    UniversityPutDTO,
)
from org.exc.collective import CollectiveNotExistsException
from org.exc.faculty import FacultyNotExistsException
from org.exc.organization import OrganizationNotExistsException
from org.exc.university import UniversityNotExistsException
from org.service.collective import CollectiveService
from org.service.faculty import FacultyService
from org.service.organization import OrganizationService
from org.service.university import UniversityService
from org.uow.collective import CollectiveUOW
from org.uow.faculty import FacultyUOW
from org.uow.organization import OrganizationUOW
from org.uow.university import UniversityUOW


@dataclass
class Case:
    service: type[Any]
    uow: type[Any]
    create_dto: type[Any]
    put_dto: type[Any]
    patch_dto: type[Any]
    filter_dto: type[Any]
    missing: type[Exception]
    module: str
    extra: dict[str, Any] = field(default_factory=dict)

    def create(self, name: str) -> Any:
        return self.create_dto(name=name, acronym="CC", **self.extra)

    def put(self, id: UUID, name: str) -> Any:
        return self.put_dto(id=id, name=name, acronym="PP", **self.extra)

    def patch(self, id: UUID, **changes: Any) -> Any:
        return self.patch_dto(id=id, fields_set=frozenset(changes), **changes)


CASES = {
    "collective": Case(
        CollectiveService,
        CollectiveUOW,
        CollectiveCreateDTO,
        CollectivePutDTO,
        CollectivePatchDTO,
        CollectiveFilterDTO,
        CollectiveNotExistsException,
        "collective",
    ),
    "faculty": Case(
        FacultyService,
        FacultyUOW,
        FacultyCreateDTO,
        FacultyPutDTO,
        FacultyPatchDTO,
        FacultyFilterDTO,
        FacultyNotExistsException,
        "faculty",
    ),
    "university": Case(
        UniversityService,
        UniversityUOW,
        UniversityCreateDTO,
        UniversityPutDTO,
        UniversityPatchDTO,
        UniversityFilterDTO,
        UniversityNotExistsException,
        "university",
    ),
    "organization": Case(
        OrganizationService,
        OrganizationUOW,
        OrganizationCreateDTO,
        OrganizationPutDTO,
        OrganizationPatchDTO,
        OrganizationFilterDTO,
        OrganizationNotExistsException,
        "organization",
        {"type": "organization"},
    ),
}


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    calls: list[tuple[str, Any]] = []

    def recorder(kind: str) -> Any:
        async def record(payload: Any) -> None:
            calls.append((kind, payload))

        return record

    for case in CASES.values():
        for kind in ("created", "updated", "deleted"):
            monkeypatch.setattr(
                f"org.service.{case.module}.on_organization_{kind}",
                recorder(kind),
            )
    return calls


@pytest.mark.parametrize("name", CASES)
async def test_crud_round_trip(
    name: str,
    org_sessionmaker: async_sessionmaker[AsyncSession],
    published: list[tuple[str, Any]],
) -> None:
    case = CASES[name]
    service = case.service(case.uow(org_sessionmaker))

    created = await service.create(case.create("First"))

    assert created.name == "First" and created.acronym is not None
    assert (await service.read(created.id)) == created
    assert published[-1][0] == "created"
    assert published[-1][1][0].id == created.id

    renamed = await service.patch(case.patch(created.id, name="Second"))
    assert renamed.name == "Second"
    assert renamed.acronym == created.acronym

    cleared = await service.patch(case.patch(created.id, acronym=None))
    assert cleared.acronym is None
    assert cleared.name == "Second"
    assert published[-1][0] == "updated"

    replaced = await service.put(case.put(created.id, "Third"))
    assert (replaced.id, replaced.name) == (created.id, "Third")

    await service.create(case.create("Other"))
    page = await service.search(case.filter_dto(), PageParamDTO(page=0, limit=1))
    assert page.pagination.total == 2
    assert len(page.items) == 1

    await service.delete(created.id)
    assert published[-1] == ("deleted", [created.id])
    with pytest.raises(case.missing):
        await service.read(created.id)


@pytest.mark.parametrize("name", CASES)
async def test_patch_of_a_missing_row_raises_not_exists(
    name: str,
    org_sessionmaker: async_sessionmaker[AsyncSession],
    published: list[tuple[str, Any]],
) -> None:
    case = CASES[name]
    service = case.service(case.uow(org_sessionmaker))

    with pytest.raises(case.missing):
        await service.patch(case.patch(uuid4(), name="Nobody"))
