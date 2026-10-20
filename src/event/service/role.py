from core.service.crud import CRUDService
from event.dto.role import RoleDTO
from event.exc.event import RoleNotExistsException
from event.filter.role import RoleFilter
from event.models.role import RoleORM
from event.uow.role import RoleUOW


class RoleService(CRUDService[RoleUOW]):
    model = RoleORM
    dto = RoleDTO
    filter_cls = RoleFilter
    not_found = RoleNotExistsException
    repo_name = "roles"
