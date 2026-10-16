from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.schema.message.geo import AddressData
from core.service.base import BaseService, required_transaction
from geo.api.kafka.pub.address import on_address_created
from geo.bootstrap.run import address_id
from geo.dto.point import PointDTO
from geo.dto.search import (
    ExternalStatusDTO,
    SearchHitDTO,
    SearchQueryDTO,
    SearchResultDTO,
)
from geo.geocoder.base import GeocodedAddress
from geo.identity import (
    DUPLICATE_RADIUS_M,
    address_key,
    meters_between,
    query_house,
    stored_key,
)
from geo.models.address import AddressORM
from geo.repository.address import Neighbour
from geo.search import tokenize
from geo.service.external import (
    MIN_QUERY_LENGTH,
    ExternalSearch,
    shared_external_search,
    shared_fallback_search,
)
from geo.service.geography import resolve_city_loose
from geo.service.live_fetch import (
    schedule_live_fetch,  # pyright: ignore[reportUnknownVariableType]
)
from geo.service.mapping import address_to_dto, location_to_dto
from geo.uow.address import AddressUOW

PLACE_RADIUS_M = 500.0
"""How close a stored address must be to lend its city to a hit that names none."""

Ranked = list[tuple[float, SearchHitDTO]]


class SearchService(BaseService[AddressUOW]):
    def __init__(
        self,
        uow: AddressUOW,
        external: ExternalSearch | None = None,
        fallback: ExternalSearch | None = None,
    ):
        super().__init__(uow)
        if external is None and fallback is None:
            external, fallback = shared_external_search(), shared_fallback_search()
        self.providers: tuple[ExternalSearch, ...] = tuple(
            provider for provider in (external, fallback) if provider is not None
        )

    @required_transaction
    async def _ranked(self, query: SearchQueryDTO, text: str) -> Ranked:
        ranked: Ranked = []
        if "address" in query.kinds:
            found = await self.uow.addresses.search_ranked(
                text, query.limit, city_id=query.city_id, near=query.near
            )
            for address, score in found:
                hit = SearchHitDTO(
                    "address", "local", score, address=address_to_dto(address)
                )
                ranked.append((-score, hit))
        if "location" in query.kinds:
            found = await self.uow.locations.search_ranked(
                text,
                query.limit,
                named_only=query.named_locations_only,
                city_id=query.city_id,
                near=query.near,
            )
            for location, score in found:
                hit = SearchHitDTO(
                    "location", "local", score, location=location_to_dto(location)
                )
                ranked.append((-score, hit))
        return ranked

    @required_transaction
    async def _nearest(self, query: SearchQueryDTO, near: PointDTO) -> Ranked:
        ranked: Ranked = []
        if "address" in query.kinds:
            found = await self.uow.addresses.nearest(
                near, query.limit, city_id=query.city_id
            )
            for address, meters in found:
                hit = SearchHitDTO(
                    "address", "local", None, address=address_to_dto(address)
                )
                ranked.append((meters, hit))
        if "location" in query.kinds:
            found = await self.uow.locations.nearest(
                near,
                query.limit,
                named_only=query.named_locations_only,
                city_id=query.city_id,
            )
            for location, meters in found:
                hit = SearchHitDTO(
                    "location", "local", None, location=location_to_dto(location)
                )
                ranked.append((meters, hit))
        return ranked

    @required_transaction
    async def _local(self, query: SearchQueryDTO, text: str) -> list[SearchHitDTO]:
        if tokenize(text):
            ranked = await self._ranked(query, text)
        elif query.near is not None:
            ranked = await self._nearest(query, query.near)
        else:
            return []
        ranked.sort(key=lambda pair: pair[0])
        return [hit for _, hit in ranked[: query.limit]]

    @required_transaction
    async def _twins(
        self, found: tuple[GeocodedAddress, ...]
    ) -> list[Neighbour | None]:
        """For each found address the stored one that is the same real address:
        the same street and house within ``DUPLICATE_RADIUS_M``, whatever city it
        was filed under."""
        around = await self.uow.addresses.neighbours(
            [(item.lat, item.lon) for item in found], DUPLICATE_RADIUS_M
        )
        twins: list[Neighbour | None] = []
        for item in found:
            key = address_key(item.street, item.housenumber)
            twin: Neighbour | None = None
            nearest = DUPLICATE_RADIUS_M
            for stored in around:
                if stored.key != key:
                    continue
                meters = meters_between(item.lat, item.lon, stored.lat, stored.lon)
                if meters <= nearest:
                    twin, nearest = stored, meters
            twins.append(twin)
        return twins

    @required_transaction
    async def _city_of(
        self, item: GeocodedAddress, cities: dict[tuple[str, str, str], int]
    ) -> int | None:
        if item.placed:
            place = (item.country, item.region, item.city)
            if place not in cities:
                cities[place] = await resolve_city_loose(self.uow, *place)
            return cities[place]
        around = await self.uow.addresses.nearest(
            PointDTO(lat=item.lat, lon=item.lon), 1
        )
        if around and around[0][1] <= PLACE_RADIUS_M:
            return around[0][0].city_id
        return None

    @required_transaction
    async def _ingest(
        self, found: tuple[GeocodedAddress, ...]
    ) -> tuple[list[SearchHitDTO], list[UUID]]:
        synced_at = datetime.now(UTC)
        cities: dict[tuple[str, str, str], int] = {}
        rows: dict[UUID, dict[str, Any]] = {}
        order: list[UUID] = []
        for item, twin in zip(found, await self._twins(found), strict=True):
            if twin is not None:
                row_id, city_id = twin.id, twin.city_id
            else:
                city = await self._city_of(item, cities)
                if city is None:
                    continue
                city_id = city
                row_id = address_id(
                    city_id,
                    item.street.strip().casefold(),
                    item.housenumber.strip().casefold(),
                )
            order.append(row_id)
            if twin is not None and twin.source != item.source:
                continue
            rows.setdefault(
                row_id,
                {
                    "id": row_id,
                    "city_id": city_id,
                    "name": item.name,
                    "spot": {"lat": item.lat, "lon": item.lon},
                    "parsed": {"house": item.housenumber, "street": item.street},
                    "source": item.source,
                    "source_id": item.source_id,
                    "synced_at": synced_at,
                },
            )
        created, _ = await self.uow.addresses.save_found(list(rows.values()))
        stored: dict[UUID, AddressORM] = {
            address.id: address
            for address in await self.uow.addresses.by_ids(list(dict.fromkeys(order)))
        }
        hits = [
            SearchHitDTO(
                "address", "external", None, address=address_to_dto(stored[row_id])
            )
            for row_id in dict.fromkeys(order)
            if row_id in stored
        ]
        return hits, created

    async def _take_external(
        self, found: tuple[GeocodedAddress, ...], known: set[UUID]
    ) -> list[SearchHitDTO]:
        async with self.uow as uow:
            hits, created = await self._ingest(found)
            await uow.commit()
        new = set(created)
        if new:
            await on_address_created(
                [
                    AddressData(id=hit.address.id, name=hit.address.name)
                    for hit in hits
                    if hit.address and hit.address.id in new
                ]
            )
        return [hit for hit in hits if hit.address and hit.address.id not in known]

    @staticmethod
    def _house_of(hit: SearchHitDTO) -> str | None:
        address = hit.address
        return stored_key(address.name, address.parsed)[1] if address else None

    @classmethod
    def _wants_external(
        cls, query: SearchQueryDTO, text: str, hits: list[SearchHitDTO]
    ) -> bool:
        """Not enough addresses, or the house the query names is not among them."""
        if not query.external or "address" not in query.kinds:
            return False
        if len(text) < MIN_QUERY_LENGTH or not tokenize(text):
            return False
        addresses = [hit for hit in hits if hit.kind == "address"]
        if len(addresses) < query.limit:
            return True
        wanted = query_house(text)
        return wanted is not None and all(
            cls._house_of(hit) != wanted for hit in addresses
        )

    @classmethod
    def _merge(
        cls,
        local: list[SearchHitDTO],
        taken: list[SearchHitDTO],
        text: str,
        limit: int,
    ) -> list[SearchHitDTO]:
        """The house the query names comes first, wherever it was found."""
        wanted = query_house(text)
        exact = [hit for hit in taken if wanted and cls._house_of(hit) == wanted]
        rest = [hit for hit in taken if hit not in exact]
        return (exact + local + rest)[:limit]

    async def search(self, query: SearchQueryDTO) -> SearchResultDTO:
        text = (query.query or "").strip()
        async with self.uow:
            hits = await self._local(query, text)

        status = ExternalStatusDTO("skipped")
        for provider in self.providers:
            if not self._wants_external(query, text, hits):
                break
            outcome = await provider.search(text, near=query.near, limit=query.limit)
            status = ExternalStatusDTO(outcome.state, outcome.provider)
            if outcome.items:
                known = {hit.address.id for hit in hits if hit.address}
                taken = await self._take_external(outcome.items, known)
                hits = self._merge(hits, taken, text, query.limit)

        if query.near is not None:
            schedule_live_fetch(
                query.near,
                sessionmaker=self.uow.session_factory,  # pyright: ignore[reportUnknownMemberType]
            )
        return SearchResultDTO(items=hits, external=status)
