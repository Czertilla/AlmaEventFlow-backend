from core.service.crud import CRUDService
from event.dto.stage import StageDTO
from event.exc.event import StageNotExistsException
from event.filter.stage import StageFilter
from event.models.stage import EventStageORM
from event.uow.stage import StageUOW


class StageService(CRUDService[StageUOW]):
    model = EventStageORM
    dto = StageDTO
    filter_cls = StageFilter
    not_found = StageNotExistsException
    repo_name = "stages"
