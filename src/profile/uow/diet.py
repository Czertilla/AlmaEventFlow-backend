from profile.repository.diet import DietRepo

from core.uow.sqlalchemy import UnitOfWork


class DietMixin:
    diets: DietRepo


class DietUOW(UnitOfWork, DietMixin): ...
