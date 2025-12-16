"""Add sim_kore_profiles table and update sim_cards

Revision ID: 011_sim_kore_profiles
Revises: 010_unit_profiles
Create Date: 2025-12-10

Cambios principales:
- Crea tabla sim_kore_profiles para almacenar datos específicos de SIM KORE
- Agrega columna updated_at a sim_cards si no existe
- Crea vista unified_sim_profiles para acceso unificado
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "011_sim_kore_profiles"
down_revision = "010_unit_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Crea tabla sim_kore_profiles y vista unified_sim_profiles
    """

    # ============================================
    # PASO 1: Agregar updated_at a sim_cards si no existe
    # ============================================
    # Verificamos si la columna existe antes de agregarla
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sim_cards' AND column_name = 'updated_at'
            """
        )
    )
    if not result.fetchone():
        op.add_column(
            "sim_cards",
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    # ============================================
    # PASO 2: Crear tabla sim_kore_profiles
    # ============================================
    # Nota: sim_id es PK y FK a la vez (relación 1:1 con sim_cards)
    op.create_table(
        "sim_kore_profiles",
        sa.Column(
            "sim_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sim_cards.sim_id"),
            primary_key=True,
        ),
        sa.Column("kore_sim_id", sa.Text(), nullable=False),
        sa.Column("kore_account_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )

    # ============================================
    # PASO 3: Crear vista unified_sim_profiles
    # ============================================
    op.execute(
        """
        CREATE OR REPLACE VIEW unified_sim_profiles AS
        SELECT
            sc.sim_id,
            sc.device_id,
            sc.carrier,
            sc.iccid,
            sc.msisdn,
            sc.imsi,
            sc.status,
            sk.kore_sim_id,
            sc.metadata
        FROM sim_cards sc
        LEFT JOIN sim_kore_profiles sk ON sc.sim_id = sk.sim_id;
        """
    )


def downgrade() -> None:
    """
    Revierte los cambios eliminando la tabla y vista
    """

    # Eliminar vista
    op.execute("DROP VIEW IF EXISTS unified_sim_profiles;")

    # Eliminar tabla
    op.drop_table("sim_kore_profiles")

    # Nota: No eliminamos updated_at de sim_cards porque puede haber sido
    # agregada manualmente antes de esta migración
