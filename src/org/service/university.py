from core.service.base import required_transaction
from org.dto.university import UniversityDTO
from org.exc.university import (
    UniversityHasFacultiesException,
    UniversityNotExistsException,
)
from org.filter.university import UniversityFilter
from org.models.university import UniversityORM
from org.service.base import OrgEntityService
from org.uow.university import UniversityUOW


class UniversityService(OrgEntityService[UniversityUOW]):
    model = UniversityORM
    dto = UniversityDTO
    filter_cls = UniversityFilter
    not_found = UniversityNotExistsException
    repo_name = "universities"

    @required_transaction
    async def _ensure_deletable(self, entity: UniversityORM) -> None:
        if await self.uow.faculties.exists_in_university(entity.id):
            raise UniversityHasFacultiesException()
