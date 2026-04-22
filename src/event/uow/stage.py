from core.uow.sqlalchemy import UnitOfWork
from event.repository.stage import EventStageRepo


class StageMixin:
    stages: EventStageRepo


class StageUOW(UnitOfWork, StageMixin): ...