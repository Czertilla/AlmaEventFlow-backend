from faststream import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.uow import ModuleUOWDep
from core.enum.mq import NotifyDeliveryQueue
from core.schema.message.notify import DeliveryResult

from notify.service.delivery import DeliveryService
from notify.uow.delivery import DeliveryResultUOW

router = KafkaRouter()

DeliveryResultUOWDep = Depends(ModuleUOWDep("notify")(DeliveryResultUOW))


@router.subscriber(NotifyDeliveryQueue.RESULT)
async def on_delivery_result(result: DeliveryResult, uow=DeliveryResultUOWDep):
    await DeliveryService(uow).apply_result(result)
