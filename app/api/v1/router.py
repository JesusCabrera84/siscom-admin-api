from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    clients,
    contact,
    device_events,
    devices,
    orders,
    payments,
    plans,
    services,
    trips,
    unit_devices,
    units,
    user_units,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(
    device_events.router, prefix="/device-events", tags=["device-events"]
)
api_router.include_router(units.router, prefix="/units", tags=["units"])
api_router.include_router(
    unit_devices.router, prefix="/unit-devices", tags=["unit-devices"]
)
api_router.include_router(user_units.router, prefix="/user-units", tags=["user-units"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(trips.router, prefix="/trips", tags=["trips"])
