import datetime
from profile.dto.contact import (
    ContactCreateDTO,
    ContactFilterDTO,
    ContactPatchDTO,
    ContactPutDTO,
)
from profile.dto.diet import (
    DietCreateDTO,
    DietFilterDTO,
    DietPatchDTO,
    DietPutDTO,
)
from profile.dto.passport import (
    NameVariantCreateDTO,
    NameVariantPatchDTO,
    NameVariantPutDTO,
    PassportCreateDTO,
    PassportFilterDTO,
    PassportPatchDTO,
    PassportPutDTO,
)
from profile.dto.person import (
    PersonCreateDTO,
    PersonFilterDTO,
    PersonPatchDTO,
    PersonPutDTO,
)
from profile.dto.profile import (
    ProfileCreateDTO,
    ProfileFilterDTO,
    ProfilePatchDTO,
    ProfilePutDTO,
)
from profile.dto.student import (
    StudentDegreeCreateDTO,
    StudentDegreeFilterDTO,
    StudentDegreePatchDTO,
    StudentFilterDTO,
    StudentGroupCreateDTO,
    StudentGroupFilterDTO,
    StudentGroupPatchDTO,
)
from profile.enum.contact import ContactType
from profile.exc.contact import ContactNotExistsException
from profile.exc.diet import DietNotExistsException
from profile.exc.person import PersonNotExistsException
from profile.exc.profile import ProfileNotExistsException
from profile.service.contact import ContactService
from profile.service.diet import DietService
from profile.service.passport import NameVariantService, PassportService
from profile.service.person import PersonService
from profile.service.profile import ProfileService
from profile.service.student import (
    StudentDegreeService,
    StudentGroupService,
    StudentService,
)
from profile.uow.diet import DietUOW
from profile.uow.passport import PassportUOW
from profile.uow.person import PersonContactUOW, PersonUOW
from profile.uow.profile import ProfileExtendedUOW, ProfilePassportUOW
from profile.uow.student import StudentUOW
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.dto.pagination import PageParamDTO

Maker = async_sessionmaker[AsyncSession]
PAGE = PageParamDTO()


def fields(*names: str) -> frozenset[str]:
    return frozenset(names)


async def _person(sm: Maker, surname: str = "Ivanov") -> UUID:
    created = await PersonService(PersonUOW(sm)).create(
        PersonCreateDTO(surname=surname, name="Ivan")
    )
    return created.id


async def _profile(sm: Maker, person_id: UUID | None = None) -> UUID:
    person_id = person_id or await _person(sm)
    created = await ProfileService(ProfileExtendedUOW(sm)).create(
        ProfileCreateDTO(id=person_id)
    )
    return created.id


async def test_diet_round_trip(profile_sessionmaker: Maker) -> None:
    service = DietService(DietUOW(profile_sessionmaker))

    created = await service.create(DietCreateDTO(name="Vegan", description="x"))
    assert (await service.read(created.id)) == created

    cleared = await service.patch(
        DietPatchDTO(id=created.id, description=None, fields_set=fields("description"))
    )
    assert (cleared.name, cleared.description) == ("Vegan", None)

    replaced = await service.put(DietPutDTO(id=created.id, name="Halal"))
    assert replaced.name == "Halal"

    page = await service.search(DietFilterDTO(), PAGE)
    assert page.pagination.total == 1

    await service.delete(created.id)
    with pytest.raises(DietNotExistsException):
        await service.read(created.id)


async def test_person_round_trip_publishes_events(
    profile_sessionmaker: Maker, published: list[tuple[str, Any]]
) -> None:
    service = PersonService(PersonUOW(profile_sessionmaker))

    created = await service.create(PersonCreateDTO(surname="Ivanov", name="Ivan"))
    assert published[-1][0] == "on_person_created"
    assert published[-1][1][0].id == created.id
    assert (await service.read(created.id)) == created

    renamed = await service.patch(
        PersonPatchDTO(id=created.id, name="Petr", fields_set=fields("name"))
    )
    assert (renamed.name, renamed.surname) == ("Petr", "Ivanov")
    assert published[-1][0] == "on_person_updated"

    replaced = await service.put(
        PersonPutDTO(id=created.id, surname="Sidorov", name="Sidor")
    )
    assert replaced.surname == "Sidorov"

    page = await service.search(PersonFilterDTO(), PAGE)
    assert [item.id for item in page.items] == [created.id]

    await service.delete(created.id)
    assert published[-1] == ("on_person_deleted", [created.id])
    with pytest.raises(PersonNotExistsException):
        await service.read(created.id)


async def test_contact_round_trip(profile_sessionmaker: Maker) -> None:
    person_id = await _person(profile_sessionmaker)
    service = ContactService(PersonContactUOW(profile_sessionmaker))

    created = await service.create(
        ContactCreateDTO(person_id=person_id, type=ContactType.email, value="a@b.c")
    )
    assert created.person_id == person_id
    assert (await service.read(created.id)) == created

    patched = await service.patch(
        ContactPatchDTO(id=created.id, is_main=True, fields_set=fields("is_main"))
    )
    assert patched.is_main and patched.value == "a@b.c"

    replaced = await service.put(
        ContactPutDTO(
            id=created.id, person_id=person_id, type=ContactType.email, value="d@e.f"
        )
    )
    assert replaced.value == "d@e.f"

    mine = await service.search_by_person(person_id, ContactFilterDTO(), PAGE)
    assert [item.id for item in mine.items] == [created.id]

    await service.delete(created.id)
    with pytest.raises(ContactNotExistsException):
        await service.read(created.id)


async def test_contact_for_an_unknown_person_is_rejected(
    profile_sessionmaker: Maker,
) -> None:
    service = ContactService(PersonContactUOW(profile_sessionmaker))

    with pytest.raises(PersonNotExistsException):
        await service.create(
            ContactCreateDTO(person_id=uuid4(), type=ContactType.email, value="a@b.c")
        )


async def test_profile_round_trip_with_its_person_and_diet(
    profile_sessionmaker: Maker,
) -> None:
    diet = await DietService(DietUOW(profile_sessionmaker)).create(
        DietCreateDTO(name="Vegan")
    )
    person_id = await _person(profile_sessionmaker)
    service = ProfileService(ProfileExtendedUOW(profile_sessionmaker))

    created = await service.create(
        ProfileCreateDTO(
            id=person_id, birthdate=datetime.date(2000, 1, 2), diet_id=diet.id
        )
    )
    read = await service.read(person_id)

    assert read.birthdate == datetime.date(2000, 1, 2)
    assert read.person is not None and read.person.id == person_id
    assert read.diet is not None and read.diet.name == "Vegan"
    assert read.created_at == created.created_at

    patched = await service.patch(
        ProfilePatchDTO(id=person_id, diet_id=None, fields_set=fields("diet_id"))
    )
    assert patched.diet_id is None

    replaced = await service.put(
        ProfilePutDTO(id=person_id, birthdate=datetime.date(1999, 3, 4))
    )
    assert replaced.birthdate == datetime.date(1999, 3, 4)

    page = await service.search(ProfileFilterDTO(), PAGE)
    assert [item.id for item in page.items] == [person_id]

    await service.ensure_existance(person_id)
    with pytest.raises(ProfileNotExistsException):
        await service.ensure_existance(uuid4())


async def test_passport_with_a_name_variant(
    profile_sessionmaker: Maker,
) -> None:
    profile_id = await _profile(profile_sessionmaker)
    passports = PassportService(ProfilePassportUOW(profile_sessionmaker))

    created = await passports.create(
        PassportCreateDTO(
            profile_id=profile_id,
            number="1234",
            expire_date=datetime.date(2030, 1, 1),
            is_foreign=False,
            name_variant=NameVariantCreateDTO(surname="Ivanova", name="Anna"),
        )
    )
    assert created.name_variant == NameVariantCreateDTO(surname="Ivanova", name="Anna")

    patched = await passports.patch(
        PassportPatchDTO(id=created.id, number="9999", fields_set=fields("number"))
    )
    assert patched.number == "9999" and patched.name_variant is not None

    mine = await passports.search_by_profile(profile_id, PassportFilterDTO(), PAGE)
    assert [item.id for item in mine.items] == [created.id]

    replaced = await passports.put(
        PassportPutDTO(
            id=created.id,
            profile_id=profile_id,
            number="7777",
            expire_date=datetime.date(2031, 1, 1),
            is_foreign=True,
        )
    )
    assert (replaced.number, replaced.is_foreign) == ("7777", True)

    await passports.delete(created.id)


async def test_name_variant_round_trip(profile_sessionmaker: Maker) -> None:
    profile_id = await _profile(profile_sessionmaker)
    passport = await PassportService(ProfilePassportUOW(profile_sessionmaker)).create(
        PassportCreateDTO(
            profile_id=profile_id,
            number="1",
            expire_date=datetime.date(2030, 1, 1),
            is_foreign=False,
        )
    )
    service = NameVariantService(PassportUOW(profile_sessionmaker))

    put = await service.put(
        NameVariantPutDTO(id=passport.id, surname="Petrova", name="Olga")
    )
    assert (await service.read(passport.id)) == put

    patched = await service.patch(
        NameVariantPatchDTO(id=passport.id, name="Maria", fields_set=fields("name"))
    )
    assert (patched.name, patched.surname) == ("Maria", "Petrova")

    await service.delete(passport.id)


async def test_student_with_group_and_degree(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    faculty_id = uuid4()
    async with profile_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO organization (id, type) VALUES (:id, 'faculty')"),
            {"id": faculty_id},
        )
    degrees = StudentDegreeService(StudentUOW(profile_sessionmaker))
    groups = StudentGroupService(StudentUOW(profile_sessionmaker))
    students = StudentService(StudentUOW(profile_sessionmaker))

    degree = await degrees.create(StudentDegreeCreateDTO(name="Bachelor"))
    renamed = await degrees.patch(
        StudentDegreePatchDTO(id=degree.id, name="Master", fields_set=fields("name"))
    )
    assert renamed.name == "Master"
    assert [
        d.id for d in (await degrees.search(StudentDegreeFilterDTO(), PAGE)).items
    ] == [degree.id]

    group = await groups.create(
        StudentGroupCreateDTO(
            name="G-1", degree_id=degree.id, faculty_id=faculty_id, grade=1
        )
    )
    regraded = await groups.patch(
        StudentGroupPatchDTO(id=group.id, grade=2, fields_set=fields("grade"))
    )
    assert regraded.grade == 2
    assert [
        g.id for g in (await groups.search(StudentGroupFilterDTO(), PAGE)).items
    ] == [group.id]

    profile_id = await _profile(profile_sessionmaker)
    async with profile_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO student (id, student_id, group_id, is_active) "
                "VALUES (:id, 'S-1', :group, true)"
            ),
            {"id": profile_id, "group": group.id},
        )

    read = await students.read(profile_id)
    assert read.student_id == "S-1"
    assert read.group is not None and read.group.name == "G-1"
    assert read.person is not None and read.person.id == profile_id
    assert read.profile is not None and read.profile.person is not None

    page = await students.search(StudentFilterDTO(), PAGE)
    assert [s.id for s in page.items] == [profile_id]
