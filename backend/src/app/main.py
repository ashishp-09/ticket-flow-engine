from fastapi import FastAPI
from starlette import status

from src.app.exceptions import (
    ConflictException,
    ForbiddenException,
    ObjectNotFoundException,
    ServiceException,
    UnauthorizedException,
)
from src.app.lifespan import app_lifespan
from src.app.routes import api_v1_router
from src.core.infra.transport.http.exception_handlers import create_exception_handler
from src.core.settings import get_settings

TAGS_METADATA = [
    {
        "name": "system",
        "description": "System health checks and diagnostics endpoints.",
    },
    {
        "name": "users",
        "description": "User authentication, registration, access tokens, and profile management.",
    },
    {
        "name": "events",
        "description": "Event lifecycle orchestration, category trees, drafts, and visitor telemetry.",
    },
    {
        "name": "orders",
        "description": "Atomic multi-ticket order creation, payment intents, webhooks, and cancellation/refunds.",
    },
    {
        "name": "tickets",
        "description": "Ticket holdings, category quotas, venue QR check-in, and peer-to-peer transfers.",
    },
    {
        "name": "admin",
        "description": "Organized administrative controls, user bans, and moderation workflows.",
    },
    {
        "name": "moderation",
        "description": "Event and organizer verification queues and approval workflows.",
    },
]

app = FastAPI(
    title="TicketFlow Engine",
    description="High-performance asynchronous backend engine for event scheduling, concurrent ticket reservations, and payment processing.",
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=app_lifespan,
)

EXCEPTION_MAPPING = {
    ServiceException: status.HTTP_400_BAD_REQUEST,
    UnauthorizedException: status.HTTP_401_UNAUTHORIZED,
    ForbiddenException: status.HTTP_403_FORBIDDEN,
    ObjectNotFoundException: status.HTTP_404_NOT_FOUND,
    ConflictException: status.HTTP_409_CONFLICT,
    ValueError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

for exception_cls, status_code in EXCEPTION_MAPPING.items():
    handler = create_exception_handler(status_code)
    app.add_exception_handler(exception_cls, handler)

app.include_router(api_v1_router)

if get_settings().enable_metrics:
    from src.app.metrics import init_metrics

    init_metrics(app)
