"""Renewal state on subscriptions: PAST_DUE status, grace period and dunning

Revision ID: 022_subscription_renewal
Revises: 021_api_idempotency
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "022_subscription_renewal"
down_revision = "021_api_idempotency"
branch_labels = None
depends_on = None

_STATUSES = ("ACTIVE", "CANCELLED", "EXPIRED", "TRIAL")

# Las columnas de dunning ya existen en los esquemas nuevos pero no en las bases
# creadas con el DDL anterior; se agregan solo si faltan.
_COLUMNS = (
    ("grace_until", sa.Column("grace_until", sa.TIMESTAMP(timezone=True))),
    ("renewal_last_error", sa.Column("renewal_last_error", sa.Text())),
    (
        "dunning_attempt_count",
        sa.Column(
            "dunning_attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    ),
    (
        "dunning_last_attempt",
        sa.Column("dunning_last_attempt", sa.TIMESTAMP(timezone=True)),
    ),
    (
        "dunning_next_attempt",
        sa.Column("dunning_next_attempt", sa.TIMESTAMP(timezone=True)),
    ),
)


def _status_check(*values: str) -> str:
    allowed = ", ".join(f"'{v}'::text" for v in values)
    return (
        "ALTER TABLE public.subscriptions "
        "DROP CONSTRAINT IF EXISTS subscriptions_status_check; "
        "ALTER TABLE public.subscriptions ADD CONSTRAINT subscriptions_status_check "
        f"CHECK (status = ANY (ARRAY[{allowed}]))"
    )


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    existing = {
        c["name"] for c in inspector.get_columns("subscriptions", schema="public")
    }
    for name, column in _COLUMNS:
        if name not in existing:
            op.add_column("subscriptions", column, schema="public")

    # Sin ampliar el CHECK, marcar una suscripción como PAST_DUE fallaría en BD.
    op.execute(sa.text(_status_check(*_STATUSES, "PAST_DUE")))

    indexes = {
        idx["name"] for idx in inspector.get_indexes("subscriptions", schema="public")
    }
    if "idx_subscriptions_due_for_renewal" not in indexes:
        # Índice parcial: el cron solo mira suscripciones cobrables, no el histórico.
        op.create_index(
            "idx_subscriptions_due_for_renewal",
            "subscriptions",
            ["expires_at"],
            postgresql_where=sa.text("auto_renew AND status IN ('ACTIVE', 'PAST_DUE')"),
            schema="public",
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())

    indexes = {
        idx["name"] for idx in inspector.get_indexes("subscriptions", schema="public")
    }
    if "idx_subscriptions_due_for_renewal" in indexes:
        op.drop_index(
            "idx_subscriptions_due_for_renewal",
            table_name="subscriptions",
            schema="public",
        )

    op.execute(
        sa.text(
            "UPDATE public.subscriptions SET status = 'EXPIRED' WHERE status = 'PAST_DUE'"
        )
    )
    op.execute(sa.text(_status_check(*_STATUSES)))

    existing = {
        c["name"] for c in inspector.get_columns("subscriptions", schema="public")
    }
    for name in ("grace_until", "renewal_last_error"):
        if name in existing:
            op.drop_column("subscriptions", name, schema="public")
