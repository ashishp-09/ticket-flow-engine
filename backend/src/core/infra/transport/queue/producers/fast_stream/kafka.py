from typing import Any

from faststream.kafka import KafkaBroker

from ..abstract import AbstractQueueProducer


class FastStreamKafkaProducer(AbstractQueueProducer):
    def __init__(self, broker: KafkaBroker) -> None:
        self._broker = broker

    async def send(self, destination: str, payload: dict[str, Any]) -> None:
        await self._broker.publish(payload, topic=destination)
