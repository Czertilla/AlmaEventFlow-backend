from profile.api.kafka.pub.person import (
    on_person_created,
    on_person_link_changed,
    on_person_updated,
)
from profile.dto.contact import ContactDTO
from profile.dto.diet import DietDTO
from profile.dto.my_profile import (
    MyProfileDTO,
    MyProfileWriteDTO,
    MyStudentReadDTO,
)
from profile.dto.student import StudentGroupDTO
from profile.exc.account import (
    AccountLinkOutOfSyncException,
    ProfileAlreadyExistsException,
)
from profile.exc.contact import ContactNotExistsException
from profile.exc.diet import DietNotExistsException
from profile.exc.organization import OrganizationNotExistsException
from profile.exc.person import PersonNotExistsException
from profile.exc.student import StudentGroupNotExistsException
from profile.models.student import StudentORM
from profile.repository.profile import ProfileRepo
from profile.uow.my_profile import MyProfileUOW
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.dto.base import dto_from_orm
from core.schema.message.profile import PersonData, PersonLinkData
from core.service.base import BaseService, required_transaction


class MyProfileService(BaseService[MyProfileUOW]):
    @staticmethod
    def _event(profile: MyProfileDTO) -> PersonData:
        return PersonData(
            id=profile.id,
            surname=profile.surname,
            name=profile.name,
            patronymic=profile.patronymic,
        )

    @required_transaction
    async def _check_references(self, data: MyProfileWriteDTO) -> None:
        if data.diet_id is not None and not await self.uow.diets.exists_id(
            data.diet_id
        ):
            raise DietNotExistsException()
        organizations = {data.workplace_id}
        if data.student is not None:
            organizations.add(data.student.faculty_id)
            if not await self.uow.student_groups.exists_id(data.student.group_id):
                raise StudentGroupNotExistsException()
        for organization_id in organizations - {None}:
            if not await self.uow.organizations.exists_id(organization_id):
                raise OrganizationNotExistsException()

    @required_transaction
    async def _ensure_free(
        self, user_id: UUID, claimed_person_id: UUID | None
    ) -> None:
        if await self.uow.account_links.get_by_user(user_id) is not None:
            raise ProfileAlreadyExistsException()
        if claimed_person_id is not None and await self.uow.persons.exists_id(
            claimed_person_id
        ):
            raise AccountLinkOutOfSyncException()

    @required_transaction
    async def _write_student(self, person_id: UUID, data: MyProfileWriteDTO) -> None:
        student = data.student
        if student is None:
            await self.uow.students.unenroll(person_id)
            return
        await self.uow.students.enroll_or_update(
            {
                "id": person_id,
                "student_id": student.student_id,
                "group_id": student.group_id,
                "faculty_id": student.faculty_id,
                "is_budget": student.is_budget,
                "is_full": student.is_full,
                "is_active": student.is_active,
            }
        )

    @required_transaction
    async def _write_contacts(self, person_id: UUID, data: MyProfileWriteDTO) -> None:
        existing = {c.id for c in await self.uow.contacts.by_person(person_id)}
        kept: set[UUID] = set()
        for contact in data.contacts:
            values = {
                "type": contact.type,
                "value": contact.value,
                "is_main": contact.is_main,
            }
            if contact.id is None:
                await self.uow.contacts.add_one({"person_id": person_id, **values})
                continue
            if contact.id not in existing:
                raise ContactNotExistsException()
            await self.uow.contacts.update_one(contact.id, values, flush=True)
            kept.add(contact.id)
        for contact_id in existing - kept:
            await self.uow.contacts.delete_one(contact_id)

    @required_transaction
    async def _write_profile(self, person_id: UUID, data: MyProfileWriteDTO) -> None:
        await self.uow.profiles.upsert(
            {
                "id": person_id,
                "birthdate": data.birthdate,
                "workplace_id": data.workplace_id,
                "diet_id": data.diet_id,
            }
        )
        await self._write_student(person_id, data)
        await self._write_contacts(person_id, data)

    @required_transaction
    async def _read(self, person_id: UUID) -> MyProfileDTO:
        person = await self.uow.persons.get_by_id(person_id)
        if person is None:
            raise PersonNotExistsException()
        profile = await self.uow.profiles.get_by_id(
            person_id, (ProfileRepo.with_diet,)
        )
        student = await self.uow.students.get_by_id(
            person_id, (selectinload(StudentORM.group),)
        )
        contacts = await self.uow.contacts.by_person(person_id)
        diet = profile.diet if profile else None
        return MyProfileDTO(
            id=person.id,
            surname=person.surname,
            name=person.name,
            patronymic=person.patronymic,
            birthdate=profile.birthdate if profile else None,
            workplace_id=profile.workplace_id if profile else None,
            diet_id=profile.diet_id if profile else None,
            diet=dto_from_orm(diet, DietDTO) if diet else None,
            student=self._student(student) if student else None,
            contacts=[dto_from_orm(contact, ContactDTO) for contact in contacts],
            created_at=person.created_at,
            edited_at=person.edited_at,
        )

    @staticmethod
    def _student(student: StudentORM) -> MyStudentReadDTO:
        group = student.group
        return MyStudentReadDTO(
            student_id=student.student_id,
            group_id=student.group_id,
            faculty_id=student.faculty_id,
            is_budget=student.is_budget,
            is_full=student.is_full,
            is_active=student.is_active,
            group=dto_from_orm(group, StudentGroupDTO) if group else None,
        )

    async def read(self, person_id: UUID) -> MyProfileDTO:
        async with self.uow:
            return await self._read(person_id)

    async def create(
        self,
        user_id: UUID,
        data: MyProfileWriteDTO,
        *,
        claimed_person_id: UUID | None = None,
    ) -> MyProfileDTO:
        try:
            async with self.uow as uow:
                await self._ensure_free(user_id, claimed_person_id)
                await self._check_references(data)
                person = await self.uow.persons.add_n_return(
                    {
                        "surname": data.surname,
                        "name": data.name,
                        "patronymic": data.patronymic,
                    }
                )
                await self.uow.account_links.add_one(
                    {"person_id": person.id, "user_id": user_id}
                )
                await self._write_profile(person.id, data)
                result = await self._read(person.id)
                await uow.commit()
        except IntegrityError as exc:
            raise ProfileAlreadyExistsException() from exc
        await on_person_created([self._event(result)])
        await on_person_link_changed(
            [PersonLinkData(user_id=user_id, person_id=result.id)]
        )
        return result

    async def replace(self, person_id: UUID, data: MyProfileWriteDTO) -> MyProfileDTO:
        async with self.uow as uow:
            await self._check_references(data)
            person = await self.uow.persons.update_one(
                person_id,
                {
                    "surname": data.surname,
                    "name": data.name,
                    "patronymic": data.patronymic,
                },
                flush=True,
            )
            if person is None:
                raise PersonNotExistsException()
            await self._write_profile(person_id, data)
            result = await self._read(person_id)
            await uow.commit()
        await on_person_updated([self._event(result)])
        return result
