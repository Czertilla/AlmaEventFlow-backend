from core.repository.person import PersonBaseRepo
from event.models.person import PersonORM as Model


class PersonRepo(PersonBaseRepo[Model]):
    model = Model
