"""Base desechable con el esquema **productivo** y las migraciones encima.

Existe porque hay dos cosas que solo se pueden comprobar sobre un esquema que
no venga de `SQLModel.metadata.create_all()`:

1. Que las migraciones aplican sobre lo que de verdad hay en produccion
   (`scripts/verificar-deriva.py`).
2. Que los objetos que solo crean las migraciones —triggers, restricciones,
   indices— se comportan como dicen (`tests/test_tenancy_esquema.py`).

El harness normal de tests no sirve para ninguna de las dos: construye el
esquema desde la metadata, asi que solo conoce lo que algun modelo declara. La
rebanada A de la Fase 2 es justamente esquema sin modelos.

El procedimiento es el del comparador de deriva: cargar el snapshot de
`tests/schema/`, stampear la revision a la que corresponde y correr
`alembic upgrade head`.
"""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parents[1]
DIR_SNAPSHOT = RAIZ / "tests" / "schema"

# El snapshot refleja el esquema productivo del 5/09/2026, anterior a la 026.
# Stamparlo aqui hace que `upgrade head` ejecute de verdad las migraciones
# posteriores, que es lo que se quiere probar.
REVISION_DEL_SNAPSHOT = os.getenv("DRIFT_STAMP", "025_device_and_unit_refs")

ESQUEMAS = ("public", "api_platform", "team", "mobility")

# Ruido conocido del snapshot: objetos que ya existen por la primera pasada, y
# referencias a _timescaledb_functions que aqui no aplican.
_ERRORES_BENIGNOS = ("already exists", "_timescaledb_functions")


def _settings():
    # Import diferido: `app.core.config` lee el entorno al importarse, y quien
    # use este modulo tiene que haber llamado antes a bootstrap_test_runtime().
    from app.core.config import settings

    return settings


def url(base: str) -> str:
    s = _settings()
    return (
        f"postgresql+psycopg2://{s.DB_USER}:{s.DB_PASSWORD}"
        f"@{s.DB_HOST}:{s.DB_PORT}/{base}"
    )


def recrear_base(base: str) -> None:
    """Deja `base` vacia, exista o no. Destructivo por definicion."""
    admin = create_engine(url("postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{base}"'))
    finally:
        admin.dispose()


def _psql(base: str, fichero: Path) -> list[str]:
    s = _settings()
    r = subprocess.run(
        [
            "psql",
            "-q",
            "-X",
            "-h",
            s.DB_HOST,
            "-p",
            str(s.DB_PORT),
            "-U",
            s.DB_USER,
            "-d",
            base,
            "-f",
            str(fichero),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PGPASSWORD": s.DB_PASSWORD or ""},
    )
    return [
        ln for ln in r.stderr.split("\n") if ln.startswith("psql:") and "ERROR" in ln
    ]


def cargar_snapshot(base: str, informar: bool = True) -> None:
    """Carga los fragmentos, en dos pasadas.

    El export vino de una herramienta grafica y no ordena por dependencias:
    dentro de un mismo fichero hay indices y restricciones que referencian
    tablas creadas mas abajo. Una sola pasada deja fuera tres tablas de `team`.

    La primera pasada se hace en silencio y la segunda es la que informa: un
    error de verdad sobrevive a las dos, mientras que uno de orden desaparece.
    """
    fragmentos = sorted(DIR_SNAPSHOT.glob("*.sql"))
    if not fragmentos:
        raise RuntimeError(f"No hay snapshot en {DIR_SNAPSHOT}")

    for f in fragmentos:  # primera pasada, silenciosa
        _psql(base, f)

    for f in fragmentos:
        errores = _psql(base, f)
        reales = [e for e in errores if not any(b in e for b in _ERRORES_BENIGNOS)]
        if not informar:
            continue
        estado = "ok" if not reales else f"{len(reales)} errores"
        if errores and not reales:
            estado = f"ok ({len(errores)} avisos conocidos)"
        print(f"  {f.name:<22} {estado}")
        for e in reales[:3]:
            print(f"      {e[:120]}")


def alembic(base: str, *args: str) -> int:
    entorno = {**os.environ, "DB_NAME": base}
    entorno.pop("DB_MIGRATION_USER", None)  # el usuario de la base local ya tiene DDL
    # `python -m alembic`, no `alembic`: el binario puede no estar en el PATH
    # (venv sin activar, CI, etc.).
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], env=entorno, cwd=str(RAIZ)
    ).returncode


def preparar(base: str, informar: bool = True) -> None:
    """Base desde cero: snapshot productivo + `alembic upgrade head`."""
    recrear_base(base)
    if informar:
        print("\n1. Cargando el snapshot del esquema productivo")
    cargar_snapshot(base, informar=informar)

    if informar:
        print(f"\n2. alembic stamp {REVISION_DEL_SNAPSHOT}")
    if alembic(base, "stamp", REVISION_DEL_SNAPSHOT) != 0:
        raise RuntimeError(f"fallo `alembic stamp {REVISION_DEL_SNAPSHOT}`")

    if informar:
        print("\n3. alembic upgrade head")
    if alembic(base, "upgrade", "head") != 0:
        raise RuntimeError(
            "las migraciones fallaron sobre el esquema real de produccion"
        )
