from core.service.crud import CRUDService
from event.dto.link import LinkDTO
from event.exc.event import LinkNotExistsException
from event.filter.link import LinkFilter
from event.models.link import EventLinkORM
from event.uow.link import LinkUOW


class LinkService(CRUDService[LinkUOW]):
    model = EventLinkORM
    dto = LinkDTO
    filter_cls = LinkFilter
    not_found = LinkNotExistsException
    repo_name = "links"
