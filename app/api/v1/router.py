"""
Router principal de la API v1.

Organiza todos los endpoints del sistema:
- API Pública (Cognito): /auth, /accounts, /organizations, /users, /subscriptions, etc.
- API Interna (PASETO): /internal/*

MODELO CONCEPTUAL:
==================
Account = Raíz comercial (billing, facturación)
Organization = Raíz operativa (permisos, uso diario)

ENDPOINTS PRINCIPALES:
======================
- POST /auth/register: Registro (crea Account + Organization + User)
- GET /auth/me: Mi Account
- POST /organizations: Crear nueva organización
- GET /organizations: Listar organizaciones del Account
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounts,
    auth,
    billing,
    capabilities,
    commands,
    contact,
    device_events,
    devices,
    orders,
    organizations,
    payments,
    plans,
    services,
    subscriptions,
    trips,
    unit_devices,
    units,
    user_units,
    users,
)
from app.api.v1.endpoints.internal import accounts as internal_accounts
from app.api.v1.endpoints.internal import organizations as internal_organizations

api_router = APIRouter()

# ============================================
# API Pública (Autenticación: Cognito)
# ============================================

# Autenticación
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Accounts (raíz comercial - onboarding + perfil progresivo)
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])

# Organizations (raíz operativa - múltiples por account)
api_router.include_router(
    organizations.router, prefix="/organizations", tags=["organizations"]
)

# Usuarios
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Suscripciones (múltiples por organización)
api_router.include_router(
    subscriptions.router, prefix="/subscriptions", tags=["subscriptions"]
)

# Capabilities (límites y features)
api_router.include_router(
    capabilities.router, prefix="/capabilities", tags=["capabilities"]
)

# Planes
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])

# Dispositivos y Unidades
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(units.router, prefix="/units", tags=["units"])
api_router.include_router(
    unit_devices.router, prefix="/unit-devices", tags=["unit-devices"]
)
api_router.include_router(user_units.router, prefix="/user-units", tags=["user-units"])
api_router.include_router(
    device_events.router, prefix="/device-events", tags=["device-events"]
)

# Servicios (legacy, considerar usar subscriptions)
api_router.include_router(services.router, prefix="/services", tags=["services"])

# Billing y Pagos (read-only)
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

# Viajes
api_router.include_router(trips.router, prefix="/trips", tags=["trips"])

# Comandos
api_router.include_router(commands.router, prefix="/commands", tags=["commands"])

# Contacto
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])

# ============================================
# API Interna (Autenticación: PASETO)
# ============================================

api_router.include_router(
    internal_accounts.router, prefix="/internal/accounts", tags=["internal-accounts"]
)
api_router.include_router(
    internal_organizations.router,
    prefix="/internal/organizations",
    tags=["internal-organizations"],
)
