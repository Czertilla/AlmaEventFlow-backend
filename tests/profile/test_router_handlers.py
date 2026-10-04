import datetime
from profile.api.v1.router.contact import patch_contact
from profile.api.v1.router.passport import patch_name_variant, patch_passport
from profile.api.v1.router.person import patch_person, put_person
from profile.api.v1.router.profile import patch_profile
from profile.api.v1.router.student import patch_student_degree, put_student_degree
from profile.api.v1.schema.contact import ContactPatch
from profile.api.v1.schema.passport import NameVariantPatchData, PassportPatchData
from profile.api.v1.schema.person import PersonPatchData, PersonPutData
from profile.api.v1.schema.profile import ProfilePatchData
from profile.api.v1.schema.student import (
    StudentDegreePatchData,
    StudentDegreePutData,
)
from profile.dto.contact import ContactCreateDTO
from profile.dto.passport import NameVariantCreateDTO, PassportCreateDTO
from profile.dto.person import PersonCreateDTO
from profile.dto.profile import ProfileCreateDTO
from profile.dto.student import StudentDegreeCreateDTO
from profile.enum.contact import ContactType
from profile.service.contact import ContactService
from profile.service.passport import PassportService
from profile.service.person import PersonService
from profile.service.profile import ProfileService
from profile.service.student import StudentDegreeService
from profile.uow.passport import PassportUOW
from profile.uow.person import PersonContactUOW, PersonUOW
from profile.uow.profile import ProfileExtendedUOW, ProfilePassportUOW
from profile.uow.student import StudentUOW
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

Maker = async_sessionmaker[AsyncSession]


async def test_person_handlers_patch_only_the_sent_fields_and_put_replaces(
    profile_sessionmaker: Maker, published: list[tuple[str, Any]]
) -> None:
    created = await PersonService(PersonUOW(profile_sessionmaker)).create(
        PersonCreateDTO(surname="Ivanov", name="Ivan")
    )

    patched = await patch_person(
        created.id,
        PersonPatchData(name="Petr"),
        user=None,
        uow=PersonUOW(profile_sessionmaker),
    )
    replaced = await put_person(
        created.id,
        PersonPutData(surname="Sidorov", name="Sidor"),
        user=None,
        uow=PersonUOW(profile_sessionmaker),
    )

    assert (patched.name, patched.surname) == ("Petr", "Ivanov")
    assert (replaced.name, replaced.surname) == ("Sidor", "Sidorov")


async def test_profile_handler_patches_only_the_sent_fields(
    profile_sessionmaker: Maker, published: list[tuple[str, Any]]
) -> None:
    person = await PersonService(PersonUOW(profile_sessionmaker)).create(
        PersonCreateDTO(surname="Ivanov", name="Ivan")
    )
    await ProfileService(ProfileExtendedUOW(profile_sessionmaker)).create(
        ProfileCreateDTO(id=person.id, birthdate=datetime.date(2000, 1, 2))
    )

    patched = await patch_profile(
        person.id,
        ProfilePatchData(),
        user=None,
        uow=ProfileExtendedUOW(profile_sessionmaker),
    )

    assert patched.birthdate == datetime.date(2000, 1, 2)


async def test_contact_handler_patches_only_the_sent_fields(
    profile_sessionmaker: Maker, published: list[tuple[str, Any]]
) -> None:
    person = await PersonService(PersonUOW(profile_sessionmaker)).create(
        PersonCreateDTO(surname="Ivanov", name="Ivan")
    )
    contact = await ContactService(PersonContactUOW(profile_sessionmaker)).create(
        ContactCreateDTO(person_id=person.id, type=ContactType.email, value="a@b.c")
    )

    patched = await patch_contact(
        user=None,
        uow=PersonContactUOW(profile_sessionmaker),
        contact=ContactPatch(id=contact.id, is_main=True),
    )

    assert patched.is_main is True
    assert patched.value == "a@b.c"


async def test_passport_handlers_patch_only_the_sent_fields(
    profile_sessionmaker: Maker, published: list[tuple[str, Any]]
) -> None:
    person = await PersonService(PersonUOW(profile_sessionmaker)).create(
        PersonCreateDTO(surname="Ivanov", name="Ivan")
    )
    await ProfileService(ProfileExtendedUOW(profile_sessionmaker)).create(
        ProfileCreateDTO(id=person.id)
    )
    passport = await PassportService(ProfilePassportUOW(profile_sessionmaker)).create(
        PassportCreateDTO(
            profile_id=person.id,
            number="1234",
            expire_date=datetime.date(2030, 1, 1),
            is_foreign=False,
            name_variant=NameVariantCreateDTO(surname="Ivanova", name="Anna"),
        )
    )

    patched = await patch_passport(
        passport.id,
        PassportPatchData(number="9999"),
        user=None,
        uow=PassportUOW(profile_sessionmaker),
    )
    renamed = await patch_name_variant(
        passport.id,
        NameVariantPatchData(name="Maria"),
        user=None,
        uow=PassportUOW(profile_sessionmaker),
    )

    assert patched.number == "9999"
    assert patched.is_foreign is False
    assert (renamed.name, renamed.surname) == ("Maria", "Ivanova")


async def test_student_degree_handlers_take_an_integer_id(
    profile_sessionmaker: Maker,
) -> None:
    degree = await StudentDegreeService(StudentUOW(profile_sessionmaker)).create(
        StudentDegreeCreateDTO(name="Bachelor")
    )

    patched = await patch_student_degree(
        degree.id,
        StudentDegreePatchData(name="Master"),
        user=None,
        uow=StudentUOW(profile_sessionmaker),
    )
    replaced = await put_student_degree(
        degree.id,
        StudentDegreePutData(name="PhD"),
        user=None,
        uow=StudentUOW(profile_sessionmaker),
    )

    assert patched.name == "Master"
    assert replaced.name == "PhD"
