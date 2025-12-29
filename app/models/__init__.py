"""
Modelos de la aplicación.

Este módulo exporta todos los modelos SQLModel utilizados en siscom-admin-api.

MODELO CONCEPTUAL:
==================
Account = Raíz comercial (billing, facturación) - SIEMPRE existe
Organization = Raíz operativa (permisos, uso diario) - SIEMPRE pertenece a Account

Relación: Account 1 ──< Organization *

En el onboarding:
1. Se crea Account
2. Se crea Organization (default, pertenece a Account)
3. Se crea User (owner de Organization)

ALIASES DE COMPATIBILIDAD:
==========================
- Client = Organization (DEPRECATED)
- ClientStatus = OrganizationStatus (DEPRECATED)
"""

# Account (raíz comercial)
from app.models.account import Account, AccountStatus

# Organization (raíz operativa, antes "Client")
from app.models.organization import Organization, OrganizationStatus

# Capabilities
from app.models.capability import (
    Capability,
    CapabilityValueType,
    OrganizationCapability,
    PlanCapability,
)

# Organization Users (roles)
from app.models.organization_user import OrganizationRole, OrganizationUser

# Users
from app.models.user import User
from app.models.invitation import Invitation

# Subscriptions & Plans
from app.models.plan import Plan
from app.models.subscription import BillingCycle, Subscription, SubscriptionStatus

# Commands
from app.models.command import Command

# Units & Devices
from app.models.unit import Unit
from app.models.unit_profile import UnitProfile
from app.models.vehicle_profile import VehicleProfile
from app.models.device import Device, DeviceEvent
from app.models.unit_device import UnitDevice
from app.models.user_unit import UserUnit

# Payments & Orders
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem, OrderItemType

# Device Services (LEGACY - no usar en código nuevo)
from app.models.device_service import (
    DeviceService,
    DeviceServiceStatus,
    SubscriptionType,
)

# Tokens
from app.models.token_confirmacion import TokenConfirmacion, TokenType

# Trips
from app.models.trip import Trip, TripAlert, TripEvent, TripPoint

# SIM Cards
from app.models.sim_card import SimCard
from app.models.sim_kore_profile import SimKoreProfile
from app.models.unified_sim_profile import UnifiedSimProfile

# ===========================================
# ALIASES DE COMPATIBILIDAD (DEPRECATED)
# ===========================================
# Estos aliases existen para compatibilidad con código existente.
# NO USAR en código nuevo. Usar Organization directamente.

Client = Organization
ClientStatus = OrganizationStatus

# ===========================================

__all__ = [
    # Account (raíz comercial)
    "Account",
    "AccountStatus",
    # Organization (raíz operativa)
    "Organization",
    "OrganizationStatus",
    "OrganizationUser",
    "OrganizationRole",
    # Aliases de compatibilidad (DEPRECATED)
    "Client",
    "ClientStatus",
    # Capabilities
    "Capability",
    "CapabilityValueType",
    "PlanCapability",
    "OrganizationCapability",
    # Users
    "User",
    "Invitation",
    # Subscriptions & Plans
    "Plan",
    "Subscription",
    "SubscriptionStatus",
    "BillingCycle",
    # Commands
    "Command",
    # Units & Devices
    "Unit",
    "UnitProfile",
    "VehicleProfile",
    "Device",
    "DeviceEvent",
    "UnitDevice",
    "UserUnit",
    # Payments & Orders
    "Payment",
    "PaymentStatus",
    "Order",
    "OrderStatus",
    "OrderItem",
    "OrderItemType",
    # Device Services (LEGACY)
    "DeviceService",
    "DeviceServiceStatus",
    "SubscriptionType",
    # Tokens
    "TokenConfirmacion",
    "TokenType",
    # Trips
    "Trip",
    "TripPoint",
    "TripAlert",
    "TripEvent",
    # SIM Cards
    "SimCard",
    "SimKoreProfile",
    "UnifiedSimProfile",
]
