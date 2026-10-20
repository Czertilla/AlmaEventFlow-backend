from org.dto.faculty import FacultyDTO
from org.exc.faculty import FacultyNotExistsException
from org.filter.faculty import FacultyFilter
from org.models.faculty import FacultyORM
from org.service.base import OrgEntityService
from org.uow.faculty import FacultyUOW


class FacultyService(OrgEntityService[FacultyUOW]):
    model = FacultyORM
    dto = FacultyDTO
    filter_cls = FacultyFilter
    not_found = FacultyNotExistsException
    repo_name = "faculties"
