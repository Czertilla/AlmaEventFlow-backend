from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.participation import ParticipationFilterDTO
from event.models.participation import ParticipationORM


class ParticipationFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = ParticipationFilterDTO

    order_by: list[str] | None = ["collective_id"]
    collective_id: None | UUID = None
    collective_id__in: None | list[UUID] = None
    event_id__in: None | list[UUID] = None

    class Constants(Filter.Constants):
        model = ParticipationORM
