from fastapi import APIRouter

from src.core.infra.cache.factory import get_cache_manager
from src.core.infra.payment.factory import get_payment_gateway
from src.modules.admin.routes import admin_router, moderation_router
from src.modules.event.routes import event_router
from src.modules.order.routes import orders_router
from src.modules.ticket.routes import ticket_router
from src.modules.user.routes import user_router

api_v1_router = APIRouter(
    prefix="/api/v1",
)

api_v1_router.include_router(moderation_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(event_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(ticket_router)
api_v1_router.include_router(user_router)


@api_v1_router.get("/healthcheck", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@api_v1_router.get("/health", tags=["system"])
async def detailed_health() -> dict[str, object]:
    cache_manager = get_cache_manager()
    payment_gw = get_payment_gateway()

    return {
        "status": "healthy",
        "service": "ticket-flow-engine",
        "version": "1.0.0",
        "subsystems": {
            "cache": cache_manager.__class__.__name__,
            "payment_gateway": payment_gw.__class__.__name__,
        }
    }
