import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.settings import get_settings

security = HTTPBearer()
SecurityDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]

# Business metrics
ORDERS_CREATED_COUNTER = Counter(
    "ticketflow_orders_created_total",
    "Total number of orders created",
    ["status"],
)

TICKETS_CHECKED_IN_COUNTER = Counter(
    "ticketflow_tickets_checked_in_total",
    "Total number of tickets successfully checked in",
)

TICKETS_TRANSFERRED_COUNTER = Counter(
    "ticketflow_tickets_transferred_total",
    "Total number of tickets transferred between attendees",
)

CHECKOUT_PROCESSING_TIME = Histogram(
    "ticketflow_checkout_duration_seconds",
    "Time spent creating checkout sessions and processing payments",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_CONNECTIONS_GAUGE = Gauge(
    "ticketflow_active_pool_connections",
    "Current number of active database pool connections",
)


def verify_metrics_token(credentials: SecurityDep):
    if not secrets.compare_digest(credentials.credentials, get_settings().metrics_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def init_metrics(app: FastAPI) -> None:
    Instrumentator().instrument(app=app)

    @app.get("/metrics", dependencies=[Depends(verify_metrics_token)], tags=["Monitoring"])
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

