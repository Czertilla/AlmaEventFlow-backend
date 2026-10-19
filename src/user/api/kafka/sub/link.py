from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.uow import ModuleUOWDep
from core.enum.topic import PersonTopic
from core.schema.message.profile import PersonLinkChangedEvent
from user.service.user import UserService
from user.uow.user import UserUOW

router = KafkaRouter()

UserUOWDep = Depends(ModuleUOWDep("user")(UserUOW))


@router.subscriber(PersonTopic.LINK_CHANGED)
async def on_person_link_changed(
    event: PersonLinkChangedEvent, uow: UserUOW = UserUOWDep
) -> None:
    await UserService(uow).apply_link(event.data)
