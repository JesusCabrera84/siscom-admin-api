from uuid import uuid4

from app.services.messaging.control_events import (
    build_unit_device_event,
    build_user_device_event,
    build_user_unit_event,
    publish_control_event,
)


def test_unit_device_event_contract():
    org = uuid4()
    unit = uuid4()
    payload = build_unit_device_event(
        event_type="UPSERT",
        device_id="0848072989",
        organization_id=org,
        unit_id=unit,
        is_active=True,
    )

    assert payload["event_type"] == "UPSERT"
    assert payload["entity"] == "unit_device"
    assert payload["organization_id"] == str(org)
    assert payload["data"]["device_id"] == "0848072989"
    assert payload["data"]["unit_id"] == str(unit)
    assert payload["data"]["is_active"] is True
    assert "event_id" in payload
    assert payload["timestamp"].endswith("Z")


def test_user_device_event_uses_row_id_and_token():
    org = uuid4()
    row_id = uuid4()
    user_id = uuid4()
    payload = build_user_device_event(
        event_type="UPSERT",
        organization_id=org,
        device_row_id=row_id,
        user_id=user_id,
        device_token="push-token",
        platform="ios",
        endpoint_arn="arn:aws:sns:test",
        is_active=True,
        updated_at=None,
    )

    assert payload["entity"] == "user_device"
    assert payload["data"]["id"] == str(row_id)
    assert payload["data"]["device_token"] == "push-token"
    assert "unit_id" not in payload["data"]
    assert payload["data"]["user_id"] == str(user_id)


def test_user_unit_delete_event():
    org = uuid4()
    user_id = uuid4()
    unit_id = uuid4()
    payload = build_user_unit_event(
        event_type="DELETE",
        organization_id=org,
        user_id=user_id,
        unit_id=unit_id,
    )
    assert payload["event_type"] == "DELETE"
    assert payload["entity"] == "user_unit"
    assert payload["data"]["user_id"] == str(user_id)
    assert payload["data"]["unit_id"] == str(unit_id)


def test_publish_control_event_swallows_producer_errors():
    class Boom:
        def publish_update(self, payload, key=None):
            raise RuntimeError("kafka down")

    publish_control_event(
        Boom(), {"entity": "unit_device", "event_type": "UPSERT"}, "k", "test"
    )
