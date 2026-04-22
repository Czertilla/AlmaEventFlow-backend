from typing import Any, Generic, Mapping, TypeVar, Union
from uuid import UUID
from beanie import BulkWriter, DeleteRules, Document, SortDirection, WriteRules
from beanie.odm.actions import ActionDirections
from beanie.odm.queries.find import FindMany
from pydantic import BaseModel  # noqa: F401
from pymongo.asynchronous.client_session import AsyncClientSession

from core.utils.abstract.repository import (
    AbstractRepository,
    AbstractIdRepository,
    AbstractSetRepository,
    AbstractCountingRepository,
)

Base = Document


Model = TypeVar("Model", bound=Base)
ID = TypeVar("ID", int, UUID, str)


class BeanieRepository(
    Generic[Model, ID],
    AbstractRepository,
    AbstractIdRepository,
    AbstractSetRepository,
    AbstractCountingRepository,
):
    model: type[Model]

    def __init__(self, session: AsyncClientSession):
        self.session = session

    async def get_one(
        self,
        *args: Mapping[Any, Any] | bool,
        projection_model: None = None,
        ignore_cache: bool = False,
        fetch_links: bool = False,
        with_children: bool = False,
        nesting_depth: int | None = None,
        nesting_depths_per_field: dict[str, int] | None = None,
        **pymongo_kwargs: Any,
    ) -> Model | None:
        return await self.model.find_one(
            *args,
            projection_model=projection_model,
            session=self.session,
            ignore_cache=ignore_cache,
            fetch_links=fetch_links,
            with_children=with_children,
            nesting_depth=nesting_depth,
            nesting_depths_per_field=nesting_depths_per_field,
            **pymongo_kwargs,
        )

    def many_generator(
        self,
        *args: Mapping[Any, Any] | bool,
        projection_model: None = None,
        skip: int | None = None,
        limit: int | None = None,
        sort: str | list[tuple[str, SortDirection]] | None = None,
        ignore_cache: bool = False,
        fetch_links: bool = False,
        with_children: bool = False,
        lazy_parse: bool = False,
        nesting_depth: int | None = None,
        nesting_depths_per_field: dict[str, int] | None = None,
        **pymongo_kwargs: Any,
    ) -> FindMany[Model]:
        return self.model.find_many(
            *args,
            projection_model=projection_model,
            skip=skip,
            limit=limit,
            sort=sort,
            session=self.session,
            ignore_cache=ignore_cache,
            fetch_links=fetch_links,
            with_children=with_children,
            lazy_parse=lazy_parse,
            nesting_depth=nesting_depth,
            nesting_depths_per_field=nesting_depths_per_field,
            **pymongo_kwargs,
        )

    async def add_one(
        self,
        doc: Model,
        link_rule: WriteRules = WriteRules.DO_NOTHING,
        session: AsyncClientSession | None = None,
        skip_actions: list[Union[ActionDirections, str]] | None = None,
    ):
        await doc.insert(session=self.session)

    async def get_many(
        self,
        *args: Mapping[Any, Any] | bool,
        projection_model: None = None,
        skip: int | None = None,
        limit: int | None = None,
        sort: str | list[tuple[str, SortDirection]] | None = None,
        ignore_cache: bool = False,
        fetch_links: bool = False,
        with_children: bool = False,
        lazy_parse: bool = False,
        nesting_depth: int | None = None,
        nesting_depths_per_field: dict[str, int] | None = None,
        **pymongo_kwargs: Any,
    ) -> list[Model]:
        return await self.many_generator(
            *args,
            projection_model=projection_model,
            skip=skip,
            limit=limit,
            sort=sort,
            ignore_cache=ignore_cache,
            fetch_links=fetch_links,
            with_children=with_children,
            lazy_parse=lazy_parse,
            nesting_depth=nesting_depth,
            nesting_depths_per_field=nesting_depths_per_field,
            **pymongo_kwargs,
        ).to_list()

    async def get_by_id(
        self,
        id: ID,
        ignore_cache: bool = False,
        fetch_links: bool = False,
        with_children: bool = False,
        nesting_depth: int | None = None,
        nesting_depths_per_field: dict[str, int] | None = None,
        **pymongo_kwargs: Any,
    ) -> Model | None:
        return await self.model.get(
            id,
            self.session,
            ignore_cache,
            fetch_links,
            with_children,
            nesting_depth,
            nesting_depths_per_field,
            **pymongo_kwargs,
        )

    async def exists_id(self, *args: Mapping[Any, Any] | bool) -> bool:
        return await self.count(*args) > 0

    async def update_one(
        self,
        doc: Model,
        *args: Union[dict[Any, Any], Mapping[Any, Any]],
        ignore_revision: bool = False,
        bulk_writer: BulkWriter | None = None,
        skip_actions: list[Union[ActionDirections, str]] | None = None,
        skip_sync: bool | None = None,
        **pymongo_kwargs: Any,
    ) -> Model:
        return await doc.update(
            *args,
            ignore_revision=ignore_revision,
            session=self.session,
            bulk_writer=bulk_writer,
            skip_actions=skip_actions,
            skip_sync=skip_sync,
            **pymongo_kwargs,
        )

    async def save(self, doc: Model):
        await doc.save(session=self.session)

    async def delete_one(
        self,
        doc: Model,
        bulk_writer: BulkWriter | None = None,
        link_rule: DeleteRules = DeleteRules.DO_NOTHING,
        skip_actions: list[ActionDirections | str] | None = None,
        **pymongo_kwargs: Any,
    ):
        await doc.delete(
            session=self.session,
            bulk_writer=bulk_writer,
            link_rule=link_rule,
            skip_actions=skip_actions,
            **pymongo_kwargs,
        )

    async def count(
        self,
        *args: Mapping[Any, Any] | bool,
    ) -> int:
        return (await self.get_many(*args)).count()

    async def count_all(self) -> int:
        return await self.model.count()
