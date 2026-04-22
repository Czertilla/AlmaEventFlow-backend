from core.uow.sqlalchemy import UnitOfWork
from profile.repository.diet import DietRepo


class DietMixin:
    diets: DietRepo


class DietUOW(UnitOfWork, DietMixin): ...
