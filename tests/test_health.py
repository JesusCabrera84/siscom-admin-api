"""Tests para app.services.health.check_kafka_accessibility."""

from unittest.mock import MagicMock

import app.services.health as health_mod


def test_check_kafka_returns_false_when_kafka_import_missing(monkeypatch):
    monkeypatch.setattr(health_mod, "KafkaProducer", None)

    assert health_mod.check_kafka_accessibility() is False


def test_check_kafka_returns_false_when_no_brokers(monkeypatch):
    monkeypatch.setattr(health_mod, "KafkaProducer", MagicMock())

    monkeypatch.setattr(health_mod.settings, "KAFKA_BROKERS", ", , ")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SECURITY_PROTOCOL", "")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SASL_USERNAME", "")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SASL_PASSWORD", "")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SASL_MECHANISM", "")

    assert health_mod.check_kafka_accessibility() is False


def test_check_kafka_returns_true_when_producer_ok(monkeypatch):
    prod = MagicMock()

    kafka_cls = MagicMock(return_value=prod)

    monkeypatch.setattr(health_mod, "KafkaProducer", kafka_cls)
    monkeypatch.setattr(health_mod.settings, "KAFKA_BROKERS", "localhost:9092")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SECURITY_PROTOCOL", "")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SASL_USERNAME", "")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SASL_PASSWORD", "")
    monkeypatch.setattr(health_mod.settings, "KAFKA_SASL_MECHANISM", "")

    assert health_mod.check_kafka_accessibility() is True

    prod.close.assert_called_once()


def test_check_kafka_returns_false_when_kafka_raises(monkeypatch):
    monkeypatch.setattr(
        health_mod,
        "KafkaProducer",
        MagicMock(side_effect=RuntimeError("broker down")),
    )
    monkeypatch.setattr(health_mod.settings, "KAFKA_BROKERS", "localhost:9092")

    assert health_mod.check_kafka_accessibility() is False


# ---------------------------------------------------------------------------
# /health contra la base de datos
#
# El endpoint devolvia un diccionario estatico. Estas pruebas fijan que ahora
# puede fallar, que es la unica razon por la que un healthcheck sirve.
# ---------------------------------------------------------------------------


def test_check_database_ok(monkeypatch):
    import app.db.session as session_mod

    conn = MagicMock()
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(session_mod, "engine", engine)

    ok, detalle = health_mod.check_database()

    assert ok is True
    assert detalle is None


def test_check_database_detecta_base_caida(monkeypatch):
    import app.db.session as session_mod

    engine = MagicMock()
    engine.connect.side_effect = RuntimeError("could not connect to server")
    monkeypatch.setattr(session_mod, "engine", engine)

    ok, detalle = health_mod.check_database()

    assert ok is False
    assert "could not connect" in detalle


def test_get_schema_revision_none_si_no_hay_alembic_version(monkeypatch):
    """Es el caso real de produccion hoy: alembic nunca gestiono el esquema."""
    import app.db.session as session_mod

    conn = MagicMock()
    conn.execute.return_value.scalar.return_value = False
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(session_mod, "engine", engine)

    assert health_mod.get_schema_revision() is None


def test_get_schema_revision_devuelve_la_revision(monkeypatch):
    import app.db.session as session_mod

    conn = MagicMock()
    conn.execute.return_value.scalar.side_effect = [True, "025_device_and_unit_refs"]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(session_mod, "engine", engine)

    assert health_mod.get_schema_revision() == "025_device_and_unit_refs"


def test_health_endpoint_devuelve_503_con_la_base_caida(client, monkeypatch):
    """El fallo que hacia inutil el healthcheck: verde con la base inservible.

    Usa el fixture `client` de conftest y no un TestClient propio: ese fixture
    stubea los productores de Kafka antes de arrancar el lifespan. Sin el, cada
    cliente nuevo intenta una conexion real a Kafka y la prueba se cuelga.
    """
    import app.main as main_mod

    monkeypatch.setattr(
        main_mod, "check_database", lambda: (False, "connection refused")
    )
    monkeypatch.setattr(main_mod, "get_schema_revision", lambda: None)

    resp = client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert body["database"] == "unreachable"
    assert body["detail"] == "connection refused"


def test_health_endpoint_ok_expone_la_revision(client, monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "check_database", lambda: (True, None))
    monkeypatch.setattr(
        main_mod, "get_schema_revision", lambda: "025_device_and_unit_refs"
    )

    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["database"] == "ok"
    assert body["schema_revision"] == "025_device_and_unit_refs"
