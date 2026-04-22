from fastapi_users_db_sqlalchemy import SQLAlchemyBaseOAuthAccountTableUUID

from core.database.sqlalchemy.core import Base
from ._base import ModuleBase


class OAuthAccountORM(ModuleBase, SQLAlchemyBaseOAuthAccountTableUUID, Base): ...
