from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from event.models.participation import ParticipationORM
from event.schema.participation import (
    ParticipationCreate,
    ParticipationPatch,
    ParticipationRead,
)
from event.uow.participation import ParticipationUOW

logger = getLogger(__name__)


class ParticipationService(BaseService[ParticipationUOW]):
    @required_transaction
    async def _create(
        self, participation_create: ParticipationCreate
    ) -> ParticipationORM:
        participation_data = participation_create.model_dump()
        participation = await self.uow.participations.add_n_return(
            data=participation_data
        )
        await self.uow.session.flush(objects=[participation])
        return participation

    @required_transaction
    async def _read(self, participation_id: UUID) -> ParticipationORM | None:
        participation = await self.uow.participations.get_by_id(
            participation_id
        )
        return participation

    @required_transaction
    async def _update(
        self,
        participation_id: UUID,
        participation_data: dict,
        *,
        flush: bool = False,
    ) -> ParticipationORM:
        participation = await self.uow.participations.update_one(
            participation_id, participation_data, flush
        )
        return participation

    @required_transaction
    async def _delete(self, participation_id: UUID) -> None:
        await self.uow.participations.delete_one(participation_id)

    async def create(
        self, participation_create: ParticipationCreate
    ) -> ParticipationRead:
        async with self.uow as uow:
            participation = await self._create(participation_create)
            result = ParticipationRead.model_validate(participation)
            await uow.commit()
        return result

    async def read(self, participation_id: UUID) -> ParticipationRead:
        async with self.uow:
            participation = await self._read(participation_id)
            return ParticipationRead.model_validate(participation)

    async def patch(
        self, participation_patch: ParticipationPatch
    ) -> ParticipationRead:
        async with self.uow as uow:
            participation_data = participation_patch.model_dump(
                exclude_unset=True
            )
            participation = await self._update(
                participation_patch.id,
                participation_data,
            )
            result = ParticipationRead.model_validate(participation)
            await uow.commit()
        return result

    async def delete(self, participation_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(participation_id)
            await uow.commit()
