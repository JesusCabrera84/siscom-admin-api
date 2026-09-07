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

La maquinaria de la base desechable vive en `tests/esquema_desechable.py`, que
comparte con los tests que ejercitan objetos que solo crean las migraciones.

LO QUE ESTA COMPROBACION NO PRUEBA
==================================
Solo mira en una direccion: que el esquema contenga lo que los modelos esperan.
Una migracion que cree tablas que ningun modelo declara —el caso de la rebanada
A de la Fase 2, que es esquema sin modelos a proposito— pasa por aqui sin que
se revise nada suyo salvo que aplique sin error. Para eso estan los tests que
la ejercitan.

Uso:
    ./scripts/db-local.sh up
    python scripts/verificar-deriva.py

Sale con codigo 1 si hay deriva.
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

# El script vive en scripts/, así que la raíz del repo no está en el path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.bootstrap_env import bootstrap_test_runtime  # noqa: E402

bootstrap_test_runtime()

from sqlmodel import SQLModel  # noqa: E402

from tests import esquema_desechable as desechable  # noqa: E402
from tests.esquema_desechable import ESQUEMAS  # noqa: E402

BASE_DERIVA = os.getenv("DRIFT_DB_NAME", "siscom_drift")


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


def _comparar() -> int:
    _registrar_modelos()
    if not SQLModel.metadata.tables:
        print("No se registro ningun modelo: la comparacion no probaria nada.")
        return 1
    eng = create_engine(desechable.url(BASE_DERIVA))
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
    from app.core.config import settings

    print(f"Base desechable: {BASE_DERIVA} en {settings.DB_HOST}:{settings.DB_PORT}")
    try:
        desechable.preparar(BASE_DERIVA)
    except RuntimeError as exc:
        print(f"\n{exc}")
        return 1

    print("\n4. Comparando modelos contra el esquema migrado")
    return _comparar()


if __name__ == "__main__":
    sys.exit(main())
