from datetime import datetime
from typing import Protocol, TypeVar
from uuid import UUID, uuid4
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import Integer, SmallInteger, BigInteger


class TimestampMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(default=func.now())

    @declared_attr
    def edited_at(cls) -> Mapped[datetime | None]:
        return mapped_column(onupdate=func.now())

ID = TypeVar('ID', int, UUID, str)

class IdMixinProtocol(Protocol):
    id: Mapped[ID]

IDMixin = TypeVar('IDMixin', bound=IdMixinProtocol)

class UUIDMixin:
    """
    Mixin class that provides a UUID primary key for database models.
    """

    @declared_attr
    def id(cls) -> Mapped[UUID]:
        """
        Defines the primary key field as a UUID.

        Returns:
            Mapped[UUID]: A mapped column with a UUID primary key.
        """
        return mapped_column(primary_key=True, default=uuid4)


class SerialMixin:
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(Integer, primary_key=True, autoincrement=True)
    
class BigSerialMixin:
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
class SmallSerialMixin:
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(SmallInteger, primary_key=True, autoincrement=True)