#!/usr/bin/env python3
"""
Sonda de reconciliacion del historial de alembic.

Responde la pregunta que bloquea la deuda de migraciones y, con ella, la Fase 2:
*a que revision hay que stampear una base que alembic nunca gestiono.*

Contexto (ver docs/adr o §19 del documento de arquitectura): el esquema tuvo dos
gestores. database-siscom/initdb creo 73 tablas, admin-api evoluciono lo suyo con
alembic, y nadie stampeo la linea base. Por eso `alembic_version` no existe y
`alembic upgrade head` sobre la base real intenta aplicar desde la 001.

La sonda NO escribe nada. Para cada revision comprueba en el esquema vivo si su
efecto ya esta presente, e informa si el resultado es un prefijo limpio
(reconciliable con un solo `alembic stamp`) o esta entreverado (hace falta una
migracion de linea base).

Uso:
    export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...
    python scripts/alembic-probe.py
"""

import os
import sys

import psycopg2

# (revision, descripcion corta, tipo de marcador, argumentos)
#
# El marcador es la huella observable del efecto de la migracion. Se elige algo
# que la migracion crea y que nada posterior deshace.
MARKERS = [
    (
        "001_update_user",
        "users.cognito_sub pasa a nullable",
        "nullable",
        ("users", "cognito_sub"),
    ),
    (
        "002_tokens_table",
        "tabla tokens_confirmacion",
        "table",
        ("tokens_confirmacion",),
    ),
    (
        "003_invitation_fields",
        "tokens_confirmacion.full_name",
        "column",
        ("tokens_confirmacion", "full_name"),
    ),
    ("004_password_temp", "users.password_temp", "column", ("users", "password_temp")),
    (
        "005_rename_device_id",
        "devices.device_id (era imei)",
        "column",
        ("devices", "device_id"),
    ),
    (
        "006_devices_events",
        "tabla device_events",
        "table",
        ("device_events",),
    ),
    ("007_units_relations", "tabla unit_devices", "table", ("unit_devices",)),
    (
        "008_add_deleted_at_to_units",
        "units.deleted_at",
        "column",
        ("units", "deleted_at"),
    ),
    (
        "009_add_preparado",
        "devices.status admite 'preparado'",
        "check",
        ("devices", "preparado"),
    ),
    ("010_unit_profiles", "tabla unit_profile", "table", ("unit_profile",)),
    (
        "011_sim_kore_profiles",
        "tabla sim_kore_profiles",
        "table",
        ("sim_kore_profiles",),
    ),
    (
        "012_add_account_id_to_organizations",
        "organizations.account_id",
        "column",
        ("organizations", "account_id"),
    ),
    (
        "013_rename_subscriptions_account_id",
        "subscriptions.organization_id",
        "column",
        ("subscriptions", "organization_id"),
    ),
    (
        "014_rename_users_client_id",
        "users.organization_id",
        "column",
        ("users", "organization_id"),
    ),
    (
        "015_subscriptions_active_units",
        "subscriptions.active_units",
        "column",
        ("subscriptions", "active_units"),
    ),
    ("016_team_core", "tabla team.teams", "table", ("team.teams",)),
    ("017_team_invites", "tabla team.invites", "table", ("team.invites",)),
    (
        "018_emergency_events",
        "tabla team.emergency_events",
        "table",
        ("team.emergency_events",),
    ),
    ("019_mobility_devices", "tabla mobility.devices", "table", ("mobility.devices",)),
    ("020_user_devices", "tabla user_devices", "table", ("user_devices",)),
    (
        "021_api_idempotency",
        "tabla api_idempotency_requests",
        "table",
        ("api_idempotency_requests",),
    ),
    (
        "022_subscription_renewal",
        "subscriptions.grace_until",
        "column",
        ("subscriptions", "grace_until"),
    ),
    (
        "023_payment_methods_schema",
        "payment_methods.method_type",
        "column",
        ("payment_methods", "method_type"),
    ),
    (
        "024_account_tax_profiles",
        "tabla account_tax_profiles",
        "table",
        ("account_tax_profiles",),
    ),
    (
        "025_device_and_unit_refs",
        "devices.device_ref",
        "column",
        ("devices", "device_ref"),
    ),
]


def connect():
    missing = [
        v for v in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER") if not os.getenv(v)
    ]
    if missing:
        sys.exit(f"Faltan variables de entorno: {', '.join(missing)}")
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.getenv("DB_PASSWORD", ""),
    )


def has_table(cur, table):
    """Acepta 'tabla' (asume public) o 'esquema.tabla'.

    Las migraciones 016-019 crean en los esquemas `team` y `mobility`, no en
    `public`: asumir public daba esas cuatro por ausentes cuando si existen.
    """
    calificada = table if "." in table else f"public.{table}"
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (calificada,))
    return cur.fetchone()[0]


def has_column(cur, table, column):
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns"
        " WHERE table_schema='public' AND table_name=%s AND column_name=%s)",
        (table, column),
    )
    return cur.fetchone()[0]


def is_nullable(cur, table, column):
    cur.execute(
        "SELECT is_nullable FROM information_schema.columns"
        " WHERE table_schema='public' AND table_name=%s AND column_name=%s",
        (table, column),
    )
    row = cur.fetchone()
    return row is not None and row[0] == "YES"


def check_contains(cur, table, needle):
    """Busca un literal dentro de las CHECK constraints de una tabla."""
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_constraint c"
        " JOIN pg_class t ON t.oid = c.conrelid"
        " WHERE t.relname=%s AND c.contype='c'"
        " AND pg_get_constraintdef(c.oid) ILIKE %s)",
        (table, f"%{needle}%"),
    )
    return cur.fetchone()[0]


def evaluate(cur, kind, args):
    if kind == "table":
        return has_table(cur, *args)
    if kind == "no_table":
        return not has_table(cur, *args)
    if kind == "column":
        return has_column(cur, *args)
    if kind == "nullable":
        return is_nullable(cur, *args)
    if kind == "check":
        return check_contains(cur, *args)
    raise ValueError(kind)


def main():
    conn = connect()
    conn.set_session(readonly=True)
    cur = conn.cursor()

    print(
        f"Base: {os.environ['DB_NAME']} en {os.environ['DB_HOST']}:{os.environ['DB_PORT']}"
    )
    print(f"Usuario: {os.environ['DB_USER']}\n")

    cur.execute(
        "SELECT count(*) FROM information_schema.tables"
        " WHERE table_schema IN ('public', 'team', 'mobility', 'api_platform')"
    )
    print(f"Tablas (public/team/mobility/api_platform): {cur.fetchone()[0]}")

    # Sin las tablas nucleo esto no es el esquema de admin-api: diagnosticar
    # revision por revision sobre una base vacia da un veredicto sin sentido,
    # porque los marcadores negativos salen todos ciertos.
    nucleo = [t for t in ("users", "devices", "organizations") if not has_table(cur, t)]
    if nucleo:
        print(f"\nFaltan tablas nucleo: {', '.join(nucleo)}")
        print("Esta base no contiene el esquema de admin-api. Nada que reconciliar.")
        cur.close()
        conn.close()
        return 0

    if has_table(cur, "alembic_version"):
        cur.execute("SELECT version_num FROM alembic_version")
        rows = [r[0] for r in cur.fetchall()]
        print(f"alembic_version: {rows or 'tabla vacia'}")
    else:
        print("alembic_version: NO EXISTE — alembic nunca gestiono este esquema")

    print(f"\n{'revision':<38} {'marcador':<40} presente")
    print("-" * 96)

    results = []
    for rev, desc, kind, args in MARKERS:
        try:
            present = evaluate(cur, kind, args)
        except psycopg2.Error:
            conn.rollback()
            present = None
        results.append((rev, present))
        mark = {True: "SI", False: "no", None: "??"}[present]
        print(f"{rev:<38} {desc:<40} {mark}")

    cur.close()
    conn.close()

    # Analisis: ¿es un prefijo limpio?
    applied = [r for r, p in results if p is True]
    absent = [r for r, p in results if p is False]

    prefix_len = 0
    for _, present in results:
        if present is True:
            prefix_len += 1
        else:
            break
    tail_all_absent = all(p is not True for _, p in results[prefix_len:])

    print("\n" + "=" * 96)
    print(f"Presentes: {len(applied)}/{len(results)}   Ausentes: {len(absent)}")

    if not applied:
        print("\nVEREDICTO: esquema vacio o ajeno. Nada que reconciliar aqui.")
        return 0

    if tail_all_absent and prefix_len == len(results):
        print("\nVEREDICTO: prefijo limpio y completo.")
        print("  Todas las migraciones estan aplicadas de hecho.")
        print(f"  Reconciliacion: alembic stamp {results[-1][0]}")
        return 0

    if tail_all_absent:
        print(f"\nVEREDICTO: prefijo limpio hasta {results[prefix_len - 1][0]}.")
        print(f"  Reconciliacion: alembic stamp {results[prefix_len - 1][0]}")
        print(
            f"  Despues, 'alembic upgrade head' aplicaria {len(results) - prefix_len} migracion(es)."
        )
        return 0

    print("\nVEREDICTO: NO MONOTONO — el esquema tiene efectos entreverados.")
    print("  Hay migraciones ausentes ANTES de migraciones presentes, asi que")
    print("  ningun 'alembic stamp' unico deja el historial correcto.")
    print("  Se necesita una migracion de linea base que declare el estado real.")
    print("\n  Huecos dentro del tramo aplicado:")
    last_present = max(i for i, (_, p) in enumerate(results) if p is True)
    for rev, present in results[: last_present + 1]:
        if present is not True:
            print(f"    - {rev} (ausente, pero hay posteriores presentes)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
