from faststream import FastStream

from src.core.infra.transport.queue.factory import get_queue_producer
from .consumers import kafka_router

broker = get_queue_producer.get_broker()
broker.include_router(kafka_router)

app = FastStream(broker)
