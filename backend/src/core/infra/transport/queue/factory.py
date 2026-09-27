from faststream.kafka import KafkaBroker
from src.core.settings import get_settings
from .producers.abstract import AbstractQueueProducer
from .producers.fast_stream.kafka import FastStreamKafkaProducer

settings = get_settings()


class QueueProducerFactory:
    def __init__(self) -> None:
        self._broker: KafkaBroker | None = None
        self._producer: AbstractQueueProducer | None = None

    def __call__(self) -> AbstractQueueProducer:
        if self._producer is None:
            self._broker = KafkaBroker(settings.kafka_url)
            self._producer = FastStreamKafkaProducer(broker=self._broker)
        return self._producer

    def get_broker(self) -> KafkaBroker:
        if self._broker is None:
            self.__call__()
        return self._broker


get_queue_producer = QueueProducerFactory()
