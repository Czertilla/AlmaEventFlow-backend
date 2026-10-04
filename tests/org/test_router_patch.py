from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.schema.user import UserJWT
from org.api.v1.router.collective import patch_collective, put_collective
from org.api.v1.router.faculty import patch_faculty
from org.api.v1.router.university import patch_university, put_university
from org.api.v1.schema.collective import CollectivePatchData, CollectivePutData
from org.api.v1.schema.faculty import FacultyPatchData
from org.api.v1.schema.university import UniversityPatchData, UniversityPutData
from org.dto.collective import CollectiveCreateDTO
from org.dto.faculty import FacultyCreateDTO
from org.dto.university import UniversityCreateDTO
from org.service.collective import CollectiveService
from org.service.faculty import FacultyService
from org.service.university import UniversityService
from org.uow.collective import CollectiveUOW
from org.uow.faculty import FacultyUOW
from org.uow.university import UniversityUOW

Maker = async_sessionmaker[AsyncSession]
ADMIN = UserJWT(id=uuid4(), is_active=True, is_verified=True, is_superuser=True)


async def test_university_handlers_patch_only_the_sent_fields_and_put_replaces(
    org_sessionmaker: Maker,
) -> None:
    created = await UniversityService(UniversityUOW(org_sessionmaker)).create(
        UniversityCreateDTO(name="MSU", acronym="M")
    )

    patched = await patch_university(
        created.id,
        UniversityPatchData(name="MSU-2"),
        user=ADMIN,
        uow=UniversityUOW(org_sessionmaker),
    )
    replaced = await put_university(
        created.id,
        UniversityPutData(name="SPbU"),
        user=ADMIN,
        uow=UniversityUOW(org_sessionmaker),
    )

    assert (patched.name, patched.acronym) == ("MSU-2", "M")
    assert (replaced.name, replaced.acronym) == ("SPbU", None)


async def test_collective_handlers_patch_only_the_sent_fields_and_put_replaces(
    org_sessionmaker: Maker,
) -> None:
    created = await CollectiveService(CollectiveUOW(org_sessionmaker)).create(
        CollectiveCreateDTO(name="Chess", acronym="CC")
    )

    patched = await patch_collective(
        created.id,
        CollectivePatchData(name="Chess club"),
        user=ADMIN,
        uow=CollectiveUOW(org_sessionmaker),
    )
    replaced = await put_collective(
        created.id,
        CollectivePutData(name="Go club"),
        user=ADMIN,
        uow=CollectiveUOW(org_sessionmaker),
    )

    assert (patched.name, patched.acronym) == ("Chess club", "CC")
    assert (replaced.name, replaced.acronym) == ("Go club", None)


async def test_faculty_handler_patches_only_the_sent_fields(
    org_sessionmaker: Maker,
) -> None:
    created = await FacultyService(FacultyUOW(org_sessionmaker)).create(
        FacultyCreateDTO(name="Math", acronym="MM")
    )

    patched = await patch_faculty(
        created.id,
        FacultyPatchData(name="Mathematics"),
        user=ADMIN,
        uow=FacultyUOW(org_sessionmaker),
    )

    assert (patched.name, patched.acronym) == ("Mathematics", "MM")
