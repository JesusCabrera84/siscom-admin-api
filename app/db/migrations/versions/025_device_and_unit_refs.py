"""Add opaque device_ref and unit_ref identifiers

Revision ID: 025_device_and_unit_refs
Revises: 024_account_tax_profiles
Create Date: 2026-08-21 10:00:00.000000

Contexto (Fase 1, aislamiento del plano de datos):

`devices.device_id` es el IMEI —la migración 005 renombró la columna `imei` a
`device_id`, no creó un identificador nuevo—, así que hoy direccionar un
dispositivo significa poner un IMEI en la URL. Ese valor acaba en los logs de
acceso de uvicorn y del ALB, y en cabeceras Referer.

`device_ref` y `unit_ref` son identificadores opacos, sin relación con el
hardware ni con las claves primarias internas, pensados para ser los únicos que
viajan al plano de datos (siscom-api). Se añaden como columnas adicionales:
`device_id` y `units.id` siguen existiendo y funcionando.

Se usa UUIDv4 para que el espacio de refs sea único aunque más adelante se
incorporen los dispositivos de `mobility.devices` (teléfonos), que hoy quedan
fuera de esta migración.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "025_device_and_unit_refs"
down_revision = "024_account_tax_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Se añade en tres pasos (nullable → backfill → NOT NULL) en lugar de
    # ADD COLUMN con default volátil: así el relleno de las filas existentes es
    # explícito y no depende del comportamiento de reescritura de PostgreSQL
    # ante un default volátil.
    op.add_column(
        "devices",
        sa.Column("device_ref", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE devices SET device_ref = gen_random_uuid() WHERE device_ref IS NULL"
    )
    op.alter_column(
        "devices",
        "device_ref",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )
    op.create_unique_constraint("uq_devices_device_ref", "devices", ["device_ref"])

    op.add_column(
        "units",
        sa.Column("unit_ref", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("UPDATE units SET unit_ref = gen_random_uuid() WHERE unit_ref IS NULL")
    op.alter_column(
        "units",
        "unit_ref",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )
    op.create_unique_constraint("uq_units_unit_ref", "units", ["unit_ref"])


def downgrade() -> None:
    op.drop_constraint("uq_units_unit_ref", "units", type_="unique")
    op.drop_column("units", "unit_ref")

    op.drop_constraint("uq_devices_device_ref", "devices", type_="unique")
    op.drop_column("devices", "device_ref")
