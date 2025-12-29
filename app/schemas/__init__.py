"""
Schemas de la aplicación.

Este módulo exporta todos los schemas Pydantic utilizados en siscom-admin-api.

MODELO CONCEPTUAL:
==================
Account = Raíz comercial (billing, facturación) - SIEMPRE existe
Organization = Raíz operativa (permisos, uso diario) - SIEMPRE pertenece a Account
"""

# Account
from app.schemas.account import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    AccountWithOrganizationsOut,
)

# Capabilities
from app.schemas.capability import (
    CapabilitiesSummaryOut,
    CapabilityOut,
    OrganizationCapabilityCreate,
    OrganizationCapabilityOut,
    ResolvedCapabilityOut,
    ValidateLimitRequest,
    ValidateLimitResponse,
)

# Client/Organization
from app.schemas.client import ClientBase, ClientCreate, ClientOut, ClientUpdate

# Commands
from app.schemas.command import (
    CommandCreate,
    CommandListResponse,
    CommandOut,
    CommandResponse,
)

# Devices
from app.schemas.device import (
    DeviceBase,
    DeviceCreate,
    DeviceOut,
    UnitBase,
    UnitCreate,
    UnitOut,
)

# Device Services
from app.schemas.device_service import (
    DeviceServiceConfirmPayment,
    DeviceServiceCreate,
    DeviceServiceOut,
    DeviceServiceWithDetails,
)

# Orders
from app.schemas.order import OrderCreate, OrderItemCreate, OrderItemOut, OrderOut

# Organization
from app.schemas.organization import (
    InviteUserRequest,
    OrganizationMemberOut,
    OrganizationMembersListOut,
    OrganizationOut,
    OrganizationSummaryOut,
    OrganizationUpdate,
    SubscriptionsListOut,
    SubscriptionSummaryOut,
    UpdateMemberRoleRequest,
)

# Payments
from app.schemas.payment import PaymentBase, PaymentCreate, PaymentOut

# Plans
from app.schemas.plan import PlanBase, PlanOut, PlanWithCapabilitiesOut, PlansListOut

# Subscriptions
from app.schemas.subscription import (
    SubscriptionCancelRequest,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionRenewRequest,
    SubscriptionWithPlanOut,
)

# Trips
from app.schemas.trip import (
    TripAlertOut,
    TripBase,
    TripDetail,
    TripEventOut,
    TripListResponse,
    TripOut,
    TripPointOut,
)

# Users
from app.schemas.user import UserBase, UserCreate, UserOut

__all__ = [
    # Account
    "AccountCreate",
    "AccountOut",
    "AccountUpdate",
    "AccountWithOrganizationsOut",
    # Capabilities
    "CapabilityOut",
    "ResolvedCapabilityOut",
    "CapabilitiesSummaryOut",
    "OrganizationCapabilityCreate",
    "OrganizationCapabilityOut",
    "ValidateLimitRequest",
    "ValidateLimitResponse",
    # Client/Organization (DEPRECATED aliases)
    "ClientBase",
    "ClientCreate",
    "ClientOut",
    "ClientUpdate",
    # Organization
    "OrganizationOut",
    "OrganizationUpdate",
    "OrganizationSummaryOut",
    "OrganizationMemberOut",
    "OrganizationMembersListOut",
    "InviteUserRequest",
    "UpdateMemberRoleRequest",
    "SubscriptionSummaryOut",
    "SubscriptionsListOut",
    # Commands
    "CommandCreate",
    "CommandResponse",
    "CommandOut",
    "CommandListResponse",
    # Users
    "UserBase",
    "UserCreate",
    "UserOut",
    # Devices
    "DeviceBase",
    "DeviceCreate",
    "DeviceOut",
    "UnitBase",
    "UnitCreate",
    "UnitOut",
    # Plans
    "PlanBase",
    "PlanOut",
    "PlanWithCapabilitiesOut",
    "PlansListOut",
    # Subscriptions
    "SubscriptionCreate",
    "SubscriptionOut",
    "SubscriptionWithPlanOut",
    "SubscriptionCancelRequest",
    "SubscriptionRenewRequest",
    # Device Services
    "DeviceServiceCreate",
    "DeviceServiceOut",
    "DeviceServiceConfirmPayment",
    "DeviceServiceWithDetails",
    # Payments
    "PaymentBase",
    "PaymentCreate",
    "PaymentOut",
    # Orders
    "OrderCreate",
    "OrderOut",
    "OrderItemCreate",
    "OrderItemOut",
    # Trips
    "TripBase",
    "TripOut",
    "TripDetail",
    "TripPointOut",
    "TripAlertOut",
    "TripEventOut",
    "TripListResponse",
]
