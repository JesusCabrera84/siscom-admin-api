#!/usr/bin/env python3
"""
Comprueba que las migraciones llevan el esquema real al que los modelos esperan.

QUE HACE, Y POR QUE ASI
=======================
Carga en una base desechable el snapshot del esquema PRODUCTIVO
(`tests/schema/`), lo stampea en la revision que le corresponde, corre
`alembic upgrade head`, y compara el resultado contra `SQLModel.metadata`.

El punto es que la base NO se construye con `create_all()`. Comparar la
metadata contra una base hecha desde esa misma metadata es tautologico: siempre
sale vacio. Solo tiene sentido cuando el esquema viene de otro sitio — aqui, de
produccion mas las migraciones.

Es la comprobacion que habria cantado la deriva de septiembre de 2026 en el PR
que la introdujo, en vez de descubrirse meses despues por un dump pedido a mano:
tres tablas ausentes con endpoint vivo —una de ellas la del cobro— y siete
columnas que impedian consultar tres modelos centrales.

Uso:
    ./scripts/db-local.sh up
    python scripts/verificar-deriva.py

Sale con codigo 1 si hay deriva.
"""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

# El script vive en scripts/, así que la raíz del repo no está en el path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.bootstrap_env import bootstrap_test_runtime  # noqa: E402

bootstrap_test_runtime()

from sqlmodel import SQLModel  # noqa: E402

from app.core.config import settings  # noqa: E402


def _registrar_modelos() -> None:
    """Puebla SQLModel.metadata. Sin esto la comparacion es de cero contra cero.

    Importar `SQLModel` no registra nada: los modelos se registran al importarse
    sus modulos. Sin esta llamada el script decia "sin deriva" habiendo revisado
    cero tablas — un verde vacio, que es exactamente lo que viene a impedir.
    """
    import app.models  # noqa: F401
    from app.api.v1.endpoints.api_platform.models import (  # noqa: F401
        api_alert,
        api_key,
        api_limit,
        api_log,
        api_throttle,
        api_usage,
    )


DIR_SNAPSHOT = Path(__file__).resolve().parents[1] / "tests" / "schema"
BASE_DERIVA = os.getenv("DRIFT_DB_NAME", "siscom_drift")

# El snapshot refleja el esquema productivo del 5/09/2026, anterior a la 026.
# Stamparlo aqui hace que `upgrade head` ejecute de verdad las migraciones
# posteriores, que es lo que se quiere probar.
REVISION_DEL_SNAPSHOT = os.getenv("DRIFT_STAMP", "025_device_and_unit_refs")

ESQUEMAS = ("public", "api_platform", "team", "mobility")


def _url(base: str) -> str:
    return (
        f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{base}"
    )


def _recrear_base() -> None:
    admin = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{BASE_DERIVA}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{BASE_DERIVA}"'))
    finally:
        admin.dispose()


def _psql(fichero: Path) -> list[str]:
    r = subprocess.run(
        [
            "psql",
            "-q",
            "-X",
            "-h",
            settings.DB_HOST,
            "-p",
            str(settings.DB_PORT),
            "-U",
            settings.DB_USER,
            "-d",
            BASE_DERIVA,
            "-f",
            str(fichero),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PGPASSWORD": settings.DB_PASSWORD or ""},
    )
    return [
        ln for ln in r.stderr.split("\n") if ln.startswith("psql:") and "ERROR" in ln
    ]


def _cargar_snapshot() -> None:
    """Carga los fragmentos, en dos pasadas.

    El export vino de una herramienta grafica y no ordena por dependencias:
    dentro de un mismo fichero hay indices y restricciones que referencian
    tablas creadas mas abajo. Una sola pasada deja fuera tres tablas de `team`.

    La primera pasada se hace en silencio y la segunda es la que informa: un
    error de verdad sobrevive a las dos, mientras que uno de orden desaparece.
    """
    fragmentos = sorted(DIR_SNAPSHOT.glob("*.sql"))
    if not fragmentos:
        sys.exit(f"No hay snapshot en {DIR_SNAPSHOT}")

    for f in fragmentos:  # primera pasada, silenciosa
        _psql(f)

    for f in fragmentos:
        # Ruido conocido del snapshot: objetos que ya existen por la primera
        # pasada, y referencias a _timescaledb_functions que aqui no aplican.
        benigno = ("already exists", "_timescaledb_functions")
        errores = _psql(f)
        reales = [e for e in errores if not any(b in e for b in benigno)]
        estado = "ok" if not reales else f"{len(reales)} errores"
        if errores and not reales:
            estado = f"ok ({len(errores)} avisos conocidos)"
        print(f"  {f.name:<22} {estado}")
        for e in reales[:3]:
            print(f"      {e[:120]}")


def _alembic(*args: str) -> int:
    entorno = {**os.environ, "DB_NAME": BASE_DERIVA}
    entorno.pop("DB_MIGRATION_USER", None)  # el usuario de la base local ya tiene DDL
    # `python -m alembic`, no `alembic`: el binario puede no estar en el PATH
    # (venv sin activar, CI, etc.).
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], env=entorno
    ).returncode


def _comparar() -> int:
    _registrar_modelos()
    if not SQLModel.metadata.tables:
        print("No se registro ningun modelo: la comparacion no probaria nada.")
        return 1
    eng = create_engine(_url(BASE_DERIVA))
    try:
        insp = inspect(eng)
        existentes = {}
        for esquema in ESQUEMAS:
            for t in insp.get_table_names(schema=esquema):
                existentes[(esquema, t)] = {
                    c["name"] for c in insp.get_columns(t, schema=esquema)
                }
    finally:
        eng.dispose()

    faltan_tablas, faltan_columnas = [], []
    for tabla in SQLModel.metadata.tables.values():
        clave = (tabla.schema or "public", tabla.name)
        if clave not in existentes:
            faltan_tablas.append(f"{clave[0]}.{clave[1]}")
            continue
        faltan = [c.name for c in tabla.columns if c.name not in existentes[clave]]
        if faltan:
            faltan_columnas.append(
                f"{clave[0]}.{clave[1]}: {', '.join(sorted(faltan))}"
            )

    print(f"\nTablas del modelo revisadas: {len(SQLModel.metadata.tables)}")
    if not faltan_tablas and not faltan_columnas:
        print(
            "Sin deriva: el esquema migrado contiene todo lo que los modelos esperan."
        )
        return 0

    print(
        f"\nDERIVA — {len(faltan_tablas)} tablas y {len(faltan_columnas)} tablas con columnas faltantes\n"
    )
    for t in sorted(faltan_tablas):
        print(f"  falta la tabla   {t}")
    for c in sorted(faltan_columnas):
        print(f"  faltan columnas  {c}")
    print(
        "\nCausa habitual: un modelo cambio y no se escribio la migracion que lo "
        "acompana. La migracion viaja en el mismo PR que el modelo."
    )
    return 1


def main() -> int:
    print(f"Base desechable: {BASE_DERIVA} en {settings.DB_HOST}:{settings.DB_PORT}")
    _recrear_base()

    print("\n1. Cargando el snapshot del esquema productivo")
    _cargar_snapshot()

    print(f"\n2. alembic stamp {REVISION_DEL_SNAPSHOT}")
    if _alembic("stamp", REVISION_DEL_SNAPSHOT) != 0:
        return 1

    print("\n3. alembic upgrade head")
    if _alembic("upgrade", "head") != 0:
        print("\nLas migraciones fallaron sobre el esquema real de produccion.")
        return 1

    print("\n4. Comparando modelos contra el esquema migrado")
    return _comparar()


if __name__ == "__main__":
    sys.exit(main())
