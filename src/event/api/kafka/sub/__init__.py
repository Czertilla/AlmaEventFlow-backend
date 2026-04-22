from core.broker.kafka import KafkaRouter
from core.utils.imports import load_common


router = KafkaRouter()

routers = load_common(__name__, "router", (KafkaRouter))
