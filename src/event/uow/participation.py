from core.uow.sqlalchemy import UnitOfWork
from event.repository.participation import ParticipationRepo


class ParticipationMixin:
    participations: ParticipationRepo


class ParticipationUOW(UnitOfWork, ParticipationMixin): ...