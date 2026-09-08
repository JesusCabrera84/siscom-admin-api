"""Tests de comportamiento en modelos Capability / Subscription (sin BD)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.capability import OrganizationCapability, PlanCapability
from app.models.subscription import SubscriptionStatus


def test_plan_capability_get_value_priority():
    pc = PlanCapability(
        plan_id=uuid4(),
        capability_id=uuid4(),
        value_int=10,
        value_bool=True,
        value_text=None,
    )
    assert pc.get_value() == 10


def test_organization_capability_is_expired():
    oc = OrganizationCapability(
        id=uuid4(),
        organization_id=uuid4(),
        capability_id=uuid4(),
        value_int=1,
        expires_at=datetime(2020, 1, 1),
    )
    assert oc.is_expired() is True


def test_organization_capability_is_expired_con_fecha_aware():
    """
    Regresion: `expires_at` es TIMESTAMP WITH TIME ZONE en la base.

    El test de arriba construye la fecha en Python, donde sale naive, asi que
    pasaba en verde mientras el codigo reventaba con un valor real leido de
    Postgres:

        TypeError: can't compare offset-naive and offset-aware datetimes

    Es el mismo fallo que tenia `Subscription.is_active()`, y estaba en el
    camino central de resolucion de capabilities: cualquier override con fecha
    de caducidad tumbaba la peticion. Se salvaba solo porque la columna la
    anadio la migracion 026 y todavia no hay filas que la usen.

    Y es la leccion de §20 en pequeno: un test que no puede fallar por la razon
    por la que falla produccion no informa de nada.
    """
    pasado = datetime.now(timezone.utc) - timedelta(days=1)
    futuro = datetime.now(timezone.utc) + timedelta(days=1)

    caducada = OrganizationCapability(
        id=uuid4(),
        organization_id=uuid4(),
        capability_id=uuid4(),
        value_int=1,
        expires_at=pasado,
    )
    vigente = OrganizationCapability(
        id=uuid4(),
        organization_id=uuid4(),
        capability_id=uuid4(),
        value_int=1,
        expires_at=futuro,
    )

    assert caducada.is_expired() is True
    assert vigente.is_expired() is False


def test_organization_capability_not_expired_when_no_expires_at():
    oc = OrganizationCapability(
        id=uuid4(),
        organization_id=uuid4(),
        capability_id=uuid4(),
        value_int=1,
        expires_at=None,
    )
    assert oc.is_expired() is False


def test_subscription_status_enum_values():
    assert SubscriptionStatus.ACTIVE.value == "ACTIVE"
