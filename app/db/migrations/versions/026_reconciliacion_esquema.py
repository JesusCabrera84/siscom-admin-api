"""Reconciliacion del esquema: pone la base al dia con la cabeza de alembic

Revision ID: 026_reconciliacion
Revises: 025_device_and_unit_refs
Create Date: 2026-09-06 00:00:00.000000

Cierra la divergencia entre el esquema real y la cadena de migraciones, medida
el 5 y 6 de septiembre de 2026 contra el DDL de produccion (ver
docs/runbooks/reconciliar-historial-alembic.md y §19/§20 del documento de
arquitectura).

POR QUE ESTA MIGRACION ES DISTINTA
==================================
Alembic nunca gestiono esta base: `alembic_version` no existia y el esquema lo
creo `database-siscom/initdb`. La sonda `scripts/alembic-probe.py` dio 21 de 25
revisiones presentes, con huecos en 004, 021, 022 y 024 — es decir, **no
monotono**: hay migraciones ausentes por debajo de otras presentes, asi que
ningun `alembic stamp` unico deja el historial correcto.

Peor aun: la 022 esta **parcialmente** aplicada. De sus cuatro columnas,
`dunning_last_attempt` y `dunning_next_attempt` existen y `grace_until` y
`renewal_last_error` no. Por eso esta migracion **no razona por migracion sino
por objeto**: comprueba y crea cada tabla y cada columna por separado. Asumir
"la 022 no esta aplicada" y reejecutarla entera fallaria.

Todo es idempotente: correrla dos veces no hace nada la segunda.

QUE REPARA (todo verificado contra produccion, no deducido)
===========================================================
Tablas ausentes con endpoint vivo:
  - api_idempotency_requests (mig. 021) — `POST /payment-intent` inserta ahi la
    reserva de idempotencia antes de llamar a Stripe. Sin la tabla, el endpoint
    de cobro falla.
  - account_tax_profiles (mig. 024) — timbrado CFDI (`cfdi_service.py`).
  - plan_products — la usa `internal/plans.py` con un JOIN. No la crea ninguna
    migracion: estaba solo en `initdb/02_schema.sql`, que nunca se ejecuto
    contra la base real.

Columnas ausentes (las siete confirmadas por consulta directa):
  - subscriptions.grace_until, renewal_last_error   (mig. 022, a medias)
  - invitations.role
  - organization_capabilities.reason, expires_at
  - order_items.created_at
  - trip_events.value

Valor de enum ausente:
  - gateway_event_status += 'processing' (lo anadia la 021).

QUE NO TOCA, A PROPOSITO
========================
  - `device_services`: el modelo la declara y `services.py` la consulta, pero la
    migracion 006 la **borra** y produccion no la tiene. Aqui produccion esta
    bien y lo que sobra es el modelo. Crearla seria resucitar algo que se
    elimino a proposito. Es una decision de producto, no de esquema.
  - `unified_sim_profiles`: existe en produccion aunque ningun artefacto la cree.
    No hay nada que reparar; queda anotada como tabla sin duenio (§19).

COMO SE APLICA
==============
    alembic stamp 025_device_and_unit_refs   # declara aplicado hasta la 025
    alembic upgrade head                     # corre solo esta

El `stamp` afirma algo falso sobre 004/021/022/024, pero esta migracion repara
exactamente esos huecos, asi que el estado final SI es verdadero. Verificar
despues de aplicar con el comparador de deriva: cero tablas y cero columnas
faltantes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "026_reconciliacion"
down_revision: Union[str, None] = "025_device_and_unit_refs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas(inspector) -> set:
    return set(inspector.get_table_names(schema="public"))


def _columnas(inspector, tabla: str) -> set:
    return {c["name"] for c in inspector.get_columns(tabla, schema="public")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tablas = _tablas(inspector)

    # ── Valor de enum que anadia la 021 ──────────────────────────────────
    # Fuera de cualquier bloque condicional: ADD VALUE IF NOT EXISTS ya es
    # idempotente, y `app/core/pg_enums.py` declara los cuatro valores.
    op.execute(
        sa.text("ALTER TYPE gateway_event_status ADD VALUE IF NOT EXISTS 'processing'")
    )

    # ── Tabla de la 021: reserva de idempotencia ─────────────────────────
    if "api_idempotency_requests" not in tablas:
        op.create_table(
            "api_idempotency_requests",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("idempotency_key", sa.Text(), nullable=False),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("request_hash", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("response_body", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "expires_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now() + interval '24 hours'"),
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.UniqueConstraint(
                "idempotency_key",
                "account_id",
                "endpoint",
                name="uq_idem_account_endpoint",
            ),
            schema="public",
        )
        op.create_index(
            "idx_idem_expires",
            "api_idempotency_requests",
            ["expires_at"],
            schema="public",
        )

    # Indice que la 021 anadia sobre payment_gateway_events.
    if "payment_gateway_events" in tablas:
        indices = {
            idx["name"]
            for idx in inspector.get_indexes("payment_gateway_events", schema="public")
        }
        if "idx_pge_failed" not in indices:
            # Columnas segun la definicion real de la 021: la tabla tiene
            # `event_status` y `processed_at`, no `status` ni `received_at`.
            op.create_index(
                "idx_pge_failed",
                "payment_gateway_events",
                ["event_status", "processed_at"],
                postgresql_where=sa.text("event_status = 'failed'"),
                schema="public",
            )

    # ── Tabla de la 024: perfiles fiscales ───────────────────────────────
    if "account_tax_profiles" not in tablas:
        op.create_table(
            "account_tax_profiles",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rfc", sa.Text(), nullable=False),
            sa.Column("legal_name", sa.Text(), nullable=False),
            sa.Column("tax_system", sa.Text(), nullable=False),
            sa.Column("zip", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column(
                "default_cfdi_use", sa.Text(), nullable=False, server_default="G03"
            ),
            sa.Column("facturapi_customer_id", sa.Text(), nullable=True),
            sa.Column(
                "facturapi_livemode",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_id", name="uq_account_tax_profiles_account"),
            schema="public",
        )

    # ── Tabla sin migracion: plan_products ───────────────────────────────
    # Solo existia en initdb/02_schema.sql, que nunca se ejecuto contra la base
    # real. La definicion sale del modelo `app/models/product.py:PlanProduct`.
    if "plan_products" not in tablas:
        op.create_table(
            "plan_products",
            sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("plan_id", "product_id"),
            schema="public",
        )

    # ── Columnas ausentes, una por una ───────────────────────────────────
    # Se vuelve a inspeccionar: las tablas creadas arriba cambian el estado.
    inspector = inspect(bind)

    faltantes = [
        # (tabla, columna, definicion)
        (
            "subscriptions",
            "grace_until",
            sa.Column("grace_until", sa.TIMESTAMP(timezone=True), nullable=True),
        ),
        (
            "subscriptions",
            "renewal_last_error",
            sa.Column("renewal_last_error", sa.Text(), nullable=True),
        ),
        (
            "invitations",
            "role",
            sa.Column("role", sa.Text(), nullable=True, server_default="member"),
        ),
        (
            "organization_capabilities",
            "reason",
            sa.Column("reason", sa.Text(), nullable=True),
        ),
        (
            "organization_capabilities",
            "expires_at",
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        ),
        (
            "order_items",
            "created_at",
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        ),
        ("trip_events", "value", sa.Column("value", sa.String(), nullable=True)),
    ]

    tablas = _tablas(inspector)
    for tabla, columna, definicion in faltantes:
        if tabla not in tablas:
            # La tabla no existe en este entorno: no es asunto de esta migracion.
            continue
        if columna not in _columnas(inspector, tabla):
            op.add_column(tabla, definicion, schema="public")


def downgrade() -> None:
    """Deshace solo lo que esta migracion pudo crear.

    Es reversible objeto por objeto, igual que el upgrade. No intenta devolver
    la base al estado divergente anterior — eso no seria deseable ni posible:
    lo que revierte es la reconciliacion, dejando el esquema como estaba antes
    de aplicarla.

    El valor 'processing' del enum NO se quita: PostgreSQL no permite eliminar
    valores de un enum, y su presencia es inocua.
    """
    bind = op.get_bind()
    inspector = inspect(bind)

    for tabla, columna in (
        ("trip_events", "value"),
        ("order_items", "created_at"),
        ("organization_capabilities", "expires_at"),
        ("organization_capabilities", "reason"),
        ("invitations", "role"),
        ("subscriptions", "renewal_last_error"),
        ("subscriptions", "grace_until"),
    ):
        if tabla in _tablas(inspector) and columna in _columnas(inspector, tabla):
            op.drop_column(tabla, columna, schema="public")

    inspector = inspect(bind)
    tablas = _tablas(inspector)

    if "plan_products" in tablas:
        op.drop_table("plan_products", schema="public")

    if "account_tax_profiles" in tablas:
        op.drop_table("account_tax_profiles", schema="public")

    if "payment_gateway_events" in tablas:
        indices = {
            idx["name"]
            for idx in inspector.get_indexes("payment_gateway_events", schema="public")
        }
        if "idx_pge_failed" in indices:
            op.drop_index("idx_pge_failed", "payment_gateway_events", schema="public")

    if "api_idempotency_requests" in tablas:
        op.drop_index("idx_idem_expires", "api_idempotency_requests", schema="public")
        op.drop_table("api_idempotency_requests", schema="public")
