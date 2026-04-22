from core.uow.event.person import PersonAUOW
from core.uow.sqlalchemy import UnitOfWork
from user.repository.person import PersonRepo

class UserPersonUOW(UnitOfWork, PersonAUOW):
    persons: PersonRepo
