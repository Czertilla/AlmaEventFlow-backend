from core.service.base import BaseService, required_transaction
from geo.dto.map import MapQueryDTO, MapViewDTO
from geo.uow.map import MapUOW


class MapService(BaseService[MapUOW]):
    @required_transaction
    async def _view(self, query: MapQueryDTO) -> MapViewDTO:
        return await self.uow.map.view(query)

    async def view(self, query: MapQueryDTO) -> MapViewDTO:
        """Single places and clusters on a grid of ``radius_px`` screen pixels."""
        async with self.uow:
            return await self._view(query)
