"""
Verificadores de salud de servicios externos.

Este módulo proporciona funciones para verificar la accesibilidad
de servicios como Kafka, bases de datos, etc.
"""

import importlib
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    kafka_module = importlib.import_module("kafka")
    KafkaProducer = kafka_module.KafkaProducer
except Exception:  # pragma: no cover
    KafkaProducer = None


def check_kafka_accessibility() -> bool:
    """
    Verifica si Kafka es accesible con las credenciales configuradas.

    Intenta crear una conexión al broker de Kafka con un timeout corto
    para evitar bloqueos al startup. Registra el resultado en el log.

    Returns:
        bool: True si Kafka es accesible, False en caso contrario
    """
    if KafkaProducer is None:
        logger.warning(
            "[STARTUP] Cliente kafka-python no disponible. "
            "Instala kafka-python para habilitar verificación de Kafka.",
            extra={
                "extra_data": {
                    "service": "kafka",
                    "status": "unavailable",
                }
            },
        )
        return False

    brokers = [
        broker.strip() for broker in settings.KAFKA_BROKERS.split(",") if broker.strip()
    ]

    if not brokers:
        logger.error(
            "[STARTUP] No hay brokers de Kafka configurados.",
            extra={
                "extra_data": {
                    "service": "kafka",
                    "status": "unconfigured",
                }
            },
        )
        return False

    config: dict[str, Any] = {
        "bootstrap_servers": brokers,
        "request_timeout_ms": 5000,
        "api_version_auto_timeout_ms": 3000,
        "connections_max_idle_ms": 5000,
    }

    if settings.KAFKA_SECURITY_PROTOCOL:
        config["security_protocol"] = settings.KAFKA_SECURITY_PROTOCOL

    if settings.KAFKA_SASL_USERNAME:
        config["sasl_plain_username"] = settings.KAFKA_SASL_USERNAME

    if settings.KAFKA_SASL_PASSWORD:
        config["sasl_plain_password"] = settings.KAFKA_SASL_PASSWORD

    if settings.KAFKA_SASL_MECHANISM:
        config["sasl_mechanism"] = settings.KAFKA_SASL_MECHANISM

    try:
        producer = KafkaProducer(**config)
        producer.close()
        logger.info(
            "[STARTUP] Kafka es accesible.",
            extra={
                "extra_data": {
                    "service": "kafka",
                    "status": "accessible",
                    "brokers": brokers,
                    "security_protocol": settings.KAFKA_SECURITY_PROTOCOL,
                }
            },
        )
        return True
    except Exception as ex:
        logger.error(
            f"[STARTUP] Kafka NO es accesible: {str(ex)}",
            extra={
                "extra_data": {
                    "service": "kafka",
                    "status": "not_accessible",
                    "brokers": brokers,
                    "error": str(ex),
                    "security_protocol": settings.KAFKA_SECURITY_PROTOCOL,
                }
            },
        )
        return False


def check_database() -> "tuple[bool, str | None]":
    """Comprueba que la base responde de verdad.

    Devuelve (ok, detalle_del_error). No propaga la excepcion: el endpoint de
    salud debe poder informar de un fallo, no morir por el.

    Existe porque /health devolvia un diccionario estatico: daba verde con la
    base inservible, y el bucle de espera del despliegue lo tomaba como senal
    de exito. Un healthcheck que no puede fallar no informa de nada.
    """
    from sqlalchemy import text

    from app.db.session import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 - cualquier fallo es un fallo de salud
        logger.warning("Health check de base de datos fallo: %s", exc)
        return False, str(exc)


def get_schema_revision() -> "str | None":
    """Revision de alembic aplicada, si la tabla existe.

    Devuelve None cuando alembic_version no existe, que es hoy el caso en
    produccion: el esquema lo creo database-siscom y nadie stampeo la linea
    base. Exponerlo en /health convierte esa ambiguedad en algo observable
    desde fuera, y permite verificar tras un despliegue que la migracion
    realmente corrio.
    """
    from sqlalchemy import text

    from app.db.session import engine

    try:
        with engine.connect() as conn:
            existe = conn.execute(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            ).scalar()
            if not existe:
                return None
            return conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer alembic_version: %s", exc)
        return None
