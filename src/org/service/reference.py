from logging import getLogger
from uuid import UUID

from core.schema.message.org import OrganizationData, OrganizationRef
from core.service.base import BaseService, required_transaction
from core.utils.names import normalize_name
from org.api.kafka.pub.organization import on_organization_created
from org.exc.organization import OrganizationNotExistsException
from org.exc.university import UniversityNotExistsException
from org.models.faculty import FacultyORM
from org.models.organization import OrganizationORM
from org.models.university import UniversityORM
from org.uow.reference import ReferenceUOW

logger = getLogger(__name__)


def _ref(organization: OrganizationORM) -> OrganizationRef:
    return OrganizationRef(
        id=organization.id, name=organization.name, type=organization.type
    )


def _announced(organization: OrganizationORM) -> OrganizationData:
    return OrganizationData(
        id=organization.id,
        name=organization.name,
        type=organization.type,
        principal_id=organization.principal_id,
    )


class ReferenceService(BaseService[ReferenceUOW]):
    @required_transaction
    async def _add(self, organization: OrganizationORM) -> OrganizationORM:
        self.uow.session.add(organization)
        await self.uow.session.flush()
        return organization

    @required_transaction
    async def _resolved(
        self, found: OrganizationORM | None, make: OrganizationORM
    ) -> OrganizationRef:
        if found is not None:
            return _ref(found)
        created = await self._add(make)
        ref, event = _ref(created), _announced(created)
        await self.uow.commit()
        await on_organization_created([event])
        return ref

    @required_transaction
    async def _university(self, name: str) -> OrganizationRef:
        found = await self.uow.universities.find_by_name(name)
        return await self._resolved(found, UniversityORM(name=name))

    @required_transaction
    async def _faculty(self, name: str, university_id: UUID) -> OrganizationRef:
        if await self.uow.universities.get_by_id(university_id) is None:
            raise UniversityNotExistsException()
        found = await self.uow.faculties.find_by_name(name, university_id)
        return await self._resolved(
            found, FacultyORM(name=name, university_id=university_id)
        )

    @required_transaction
    async def _organization(self, name: str) -> OrganizationRef:
        found = await self.uow.organizations.find_workplace(name)
        return await self._resolved(found, OrganizationORM(name=name))

    @required_transaction
    async def _get(self, organization_id: UUID) -> OrganizationRef:
        found = await self.uow.organizations.get_by_id(organization_id)
        if found is None:
            raise OrganizationNotExistsException()
        return _ref(found)

    async def university(self, name: str) -> OrganizationRef:
        async with self.uow:
            return await self._university(normalize_name(name))

    async def faculty(self, name: str, university_id: UUID) -> OrganizationRef:
        async with self.uow:
            return await self._faculty(normalize_name(name), university_id)

    async def organization(self, name: str) -> OrganizationRef:
        async with self.uow:
            return await self._organization(normalize_name(name))

    async def get(self, organization_id: UUID) -> OrganizationRef:
        async with self.uow:
            return await self._get(organization_id)
