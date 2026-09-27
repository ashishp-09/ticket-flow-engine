from typing import Any, Dict, List

from faststream import Logger
from faststream.kafka import KafkaRouter

from .annotations import ViewLogServiceDep

kafka_router = KafkaRouter()


@kafka_router.subscriber(
    "view_logs_queue",
    batch=True,
    max_records=500,
    batch_timeout_ms=6000,
    fetch_min_bytes=1024 * 64,
    fetch_max_wait_ms=5000,
    consumer_timeout_ms=5000,
)
async def handle_view_logs(
        payloads: List[Dict[str, Any]],
        service: ViewLogServiceDep,
        logger: Logger
) -> None:
    total_logs = sum(len(p.get("object_ids", [])) for p in payloads)

    logger.info(f"Received batch of {len(payloads)} messages with {total_logs} total logs.")

    try:
        processed = await service.process_view_logs(payloads=payloads)
        logger.info(f"Successfully inserted {processed} out of {total_logs} logs.")
    except Exception as e:
        logger.exception(f"Failed to process batch of {total_logs} logs. Error: {e}")
        raise
