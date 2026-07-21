"""cascade deletes and ticket number trigger

Revision ID: 75b19a82dd29
Revises: 2bf16b19d1ac
Create Date: 2026-07-20 17:04:58.120044

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "75b19a82dd29"
down_revision: Union[str, Sequence[str], None] = "2bf16b19d1ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Cascade deletes at the DB level - replaces SQLAlchemy's ORM-level
    # cascade="all, delete-orphan", which has no equivalent once queries go
    # through the Supabase client instead of an ORM session.
    op.drop_constraint("ticket_activity_ticket_id_fkey", "ticket_activity", type_="foreignkey")
    op.create_foreign_key(
        "ticket_activity_ticket_id_fkey",
        "ticket_activity",
        "tickets",
        ["ticket_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("ticket_messages_ticket_id_fkey", "ticket_messages", type_="foreignkey")
    op.create_foreign_key(
        "ticket_messages_ticket_id_fkey",
        "ticket_messages",
        "tickets",
        ["ticket_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ticket_number generation moves into the database: a BEFORE INSERT
    # trigger sets it from the row's own id. Postgres evaluates a SERIAL/
    # IDENTITY column's default *before* a BEFORE INSERT trigger runs, so
    # NEW.id is already populated here - one atomic insert, no app-level
    # flush-then-update needed (see backend/services/ticket_service.py).
    op.execute(
        """
        CREATE FUNCTION set_ticket_number() RETURNS trigger AS $$
        BEGIN
            NEW.ticket_number := 'TKT-' || lpad(NEW.id::text, 5, '0');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_set_ticket_number
        BEFORE INSERT ON tickets
        FOR EACH ROW EXECUTE FUNCTION set_ticket_number();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_set_ticket_number ON tickets;")
    op.execute("DROP FUNCTION IF EXISTS set_ticket_number();")

    op.drop_constraint("ticket_messages_ticket_id_fkey", "ticket_messages", type_="foreignkey")
    op.create_foreign_key(
        "ticket_messages_ticket_id_fkey",
        "ticket_messages",
        "tickets",
        ["ticket_id"],
        ["id"],
    )
    op.drop_constraint("ticket_activity_ticket_id_fkey", "ticket_activity", type_="foreignkey")
    op.create_foreign_key(
        "ticket_activity_ticket_id_fkey",
        "ticket_activity",
        "tickets",
        ["ticket_id"],
        ["id"],
    )
