from datetime import datetime
from logging import Logger, getLogger
from typing import Any, ClassVar, Self, cast

from sqlalchemy import (
    Executable,
    Result,
    ScalarResult,
    SQLColumnExpression,
    exists,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.types import DateTime

from ...utils.abstract.repository import AbstractRepository
from .session import settings

if settings.DB_DBMS == "postgres":
    from sqlalchemy.dialects.postgresql import JSONB as JSON
else:
    from sqlalchemy import JSON

class BasePreference:
    
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: JSON,
        datetime: DateTime(timezone=True),
    }

class Base(BasePreference, DeclarativeBase):
    __abstract__ = True
    
    type_annotation_map = BasePreference.type_annotation_map


class SQLAlchemyRepository[Model: Base](AbstractRepository):
    """
    Asynchronous repository for performing database operations using SQLAlchemy.

    Attributes:
        model (type[Base]): The SQLAlchemy model class.
        logger (Logger): Logger instance for logging SQL operations.
    """

    model: type[Model]
    logger: Logger

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if not hasattr(cls, "logger"):
            cls.logger = getLogger(f"SQL.{cls.__name__}")
        return super().__new__(cls)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session: AsyncSession = session

    async def execute(self, stmt: Executable, flush: bool = False) -> Result[Any]:
        self.logger.debug(str(stmt))
        result: Result[Any] = await self.session.execute(statement=stmt)
        if flush:
            await self.session.flush()
        return result

    async def flush(self) -> None:
        await self.session.flush()

    async def get(self, id: Any) -> Model | None:
        return await self.session.get(self.model, id)

    async def merge(self, data_orm: Model, flush: bool = False) -> None:
        await self.session.merge(data_orm)
        if flush:
            await self.session.flush()

    async def add_one(self, data: dict[str, Any]) -> None:
        stmt = insert(self.model).values(**data)
        await self.execute(stmt, flush=True)

    async def add_entity(self, entity: Model) -> Model:
        """Adds an ORM instance and flushes it, so its defaults are filled in."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_n_return(
        self, data: dict[str, Any], options: tuple[Any, ...] = ()
    ) -> Model:
        stmt = (
            insert(self.model)
            .values(**data)
            .returning(self.model)
            .options(*options)
        )
        return (await self.execute(stmt, flush=True)).unique().scalar_one()
    
    async def add_many(
        self, data: list[dict[str, Any]], options: tuple[ExecutableOption, ...] = ()
    ) -> ScalarResult[Model]:
        stmt = (
            insert(self.model)
            .values(data)
            .returning(self.model)
            .options(*options)
        )
        return (await self.execute(stmt, flush=True)).unique().scalars()

    async def get_many(
        self,
        *criterias: SQLColumnExpression[bool],
        offset_: int | None = None,
        limit_: int | None = None,
        options_: tuple[ExecutableOption, ...] = (),
        order_by_: list[SQLColumnExpression[Any]] | None = None,
        **filters: Any,
    ) -> list[Model]:
        stmt = (
            select(self.model)
            .where(*criterias)
            .filter_by(**filters)
            .options(*options_)
        )
        if order_by_:
            stmt = stmt.order_by(*order_by_)
        if offset_:
            stmt = stmt.offset(offset_)
        if limit_:
            stmt = stmt.limit(limit_)
        else:
            self.logger.warning(
                f"Using {self.__class__.__name__}.get_many method without "
                + "async defining the limit_ parameter can lead to memory overflow"
            )
        result = await self.execute(stmt)
        return cast("list[Model]", result.scalars().all())

    async def get_one(
        self,
        *criterias: SQLColumnExpression[bool],
        options_: list[ExecutableOption] | None = None,
        **filters: Any,
    ) -> Model | None:
        stmt = (
            select(self.model)
            .where(*criterias)
            .filter_by(**filters)
            .options(*(options_ or ()))
        )
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def exists(self, *criterias: SQLColumnExpression[bool]) -> bool:
        return (await self.execute(select(exists().where(*criterias)))).scalar()

    async def count(self, *criterias: SQLColumnExpression[bool]) -> int:
        stmt = select(func.count()).select_from(self.model)
        if criterias:
            stmt = stmt.where(*criterias)
        return (await self.execute(stmt)).scalar_one()
