from org.dto.collective import CollectiveDTO
from org.exc.collective import CollectiveNotExistsException
from org.filter.collective import CollectiveFilter
from org.models.collective import CollectiveORM
from org.service.base import UniversityLinkedService
from org.uow.collective import CollectiveUOW


class CollectiveService(UniversityLinkedService[CollectiveUOW]):
    model = CollectiveORM
    dto = CollectiveDTO
    filter_cls = CollectiveFilter
    not_found = CollectiveNotExistsException
    repo_name = "collectives"
