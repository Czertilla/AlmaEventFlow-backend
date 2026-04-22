from core.schema.message.profile import PersonData
from core.service.base import required_transaction
from core.service.event.person import PersonEventService
from user.uow.person import UserPersonUOW

class UserPersonEventService(PersonEventService[UserPersonUOW]):

    @required_transaction
    async def _create(self, person: PersonData):
        await self.uow.persons.add_n_return(data={"id": person.id})

    @required_transaction
    async def _upsert(self, person: PersonData):
        await self.uow.persons.upsert(data={"id": person.id})