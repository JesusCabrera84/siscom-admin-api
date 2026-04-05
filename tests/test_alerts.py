from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import status

from app.models.alert import Alert
from app.models.organization import Organization
from app.models.unit import Unit


def _create_unit(db_session, organization_id, name):
    unit = Unit(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        description="Unidad de prueba",
    )
    db_session.add(unit)
    db_session.commit()
    db_session.refresh(unit)
    return unit


def test_get_alerts_filtered_by_unit(
    authenticated_client, db_session, test_user_data
):
    unit_1 = _create_unit(db_session, test_user_data.organization_id, "Unidad 1")
    unit_2 = _create_unit(db_session, test_user_data.organization_id, "Unidad 2")

    older = datetime.utcnow() - timedelta(minutes=10)
    newer = datetime.utcnow()

    alert_1 = Alert(
        organization_id=test_user_data.organization_id,
        unit_id=unit_1.id,
        source_type="event",
        source_id="evt-1",
        type="ignition_off",
        payload={"event": "Engine OFF"},
        occurred_at=older,
    )
    alert_2 = Alert(
        organization_id=test_user_data.organization_id,
        unit_id=unit_1.id,
        source_type="event",
        source_id="evt-2",
        type="ignition_off",
        payload={"event": "Engine OFF"},
        occurred_at=newer,
    )
    alert_other_unit = Alert(
        organization_id=test_user_data.organization_id,
        unit_id=unit_2.id,
        source_type="event",
        source_id="evt-3",
        type="geofence_enter",
        payload={"event": "Geofence Enter"},
        occurred_at=newer,
    )

    db_session.add(alert_1)
    db_session.add(alert_2)
    db_session.add(alert_other_unit)
    db_session.commit()

    response = authenticated_client.get(f"/api/v1/alerts?unit_id={unit_1.id}")
    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert len(items) == 2
    assert all(item["unit_id"] == str(unit_1.id) for item in items)
    assert items[0]["occurred_at"] >= items[1]["occurred_at"]


def test_get_alerts_rejects_unit_from_other_org(
    authenticated_client, db_session, test_account_data, test_user_data
):
    other_org = Organization(
        id=uuid4(),
        account_id=test_account_data.id,
        name="Otra org",
        status="ACTIVE",
    )
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    other_unit = _create_unit(db_session, other_org.id, "Unidad externa")

    response = authenticated_client.get(f"/api/v1/alerts?unit_id={other_unit.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_alerts_returns_empty_when_org_inactive(
    authenticated_client, db_session, test_user_data
):
    unit = _create_unit(db_session, test_user_data.organization_id, "Unidad 1")

    alert = Alert(
        organization_id=test_user_data.organization_id,
        unit_id=unit.id,
        source_type="event",
        source_id="evt-1",
        type="ignition_off",
        payload={"event": "Engine OFF"},
        occurred_at=datetime.utcnow(),
    )
    db_session.add(alert)
    db_session.commit()

    org = (
        db_session.query(Organization)
        .filter(Organization.id == test_user_data.organization_id)
        .first()
    )
    org.status = "SUSPENDED"
    db_session.add(org)
    db_session.commit()

    response = authenticated_client.get(f"/api/v1/alerts?unit_id={unit.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
