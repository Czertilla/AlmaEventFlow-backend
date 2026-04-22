from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin


class CollectiveAORM(Base, UUIDMixin):
    __tablename__ = "collective"
    __abstract__ = True
