from fastapi import APIRouter

from app.api import admin, auth, event, reservation, webhooks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(event.router, prefix="/events", tags=["Events"])
api_router.include_router(
    reservation.router, prefix="/reservations", tags=["Reservations"]
)
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
