from profile.api.v2.schema.person import (
    PersonNameRead,
    PersonNamesData,
    PersonNamesRead,
)
from profile.dependency.access import PolicyDep
from profile.dependency.person import PersonUOWDep
from profile.registry import PERSON_FULLNAME
from profile.service.person import PersonService

from fastapi import APIRouter

from core.schema.error import auth_responses

router = APIRouter(prefix="/persons", tags=["person"])


@router.post("/names", responses={**auth_responses()})
async def get_person_names(
    data: PersonNamesData, policy: PolicyDep, uow: PersonUOWDep
) -> PersonNamesRead:
    """The full names of the requested persons.

    Every requested id gets an entry. The name is left out when the caller may not see
    it or the person does not exist: the two look the same.
    """
    decisions = await policy.decide(data.ids, PERSON_FULLNAME)
    allowed = [person_id for person_id, decision in decisions.items() if decision.allow]
    return PersonNamesRead(
        items=[
            PersonNameRead.from_dto(name)
            for name in await PersonService(uow).names(data.ids, allowed)
        ]
    )
