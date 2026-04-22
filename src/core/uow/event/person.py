from core.repository.person import PersonBaseRepo
from core.utils.abstract.unit_of_work import ABCUnitOfWork


class PersonAUOW(ABCUnitOfWork):
    persons: PersonBaseRepo