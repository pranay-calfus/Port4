"""add feedback updated at trigger

Revision ID: 4343a7aeb8d0
Revises: 8f5865b86386
Create Date: 2026-07-21 14:15:47.060755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4343a7aeb8d0'
down_revision: Union[str, Sequence[str], None] = '8f5865b86386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # feedback.updated_at is only given an initial value by its server
    # default - keep it current on every UPDATE via the same set_updated_at()
    # trigger function used by users/tickets (see the "server-side defaults
    # and updated_at triggers" migration), since create_feedback_from_chat
    # does a second UPDATE (writing the classification result) after the
    # initial insert.
    op.execute(
        """
        CREATE TRIGGER trg_feedback_updated_at
        BEFORE UPDATE ON feedback
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_feedback_updated_at ON feedback;")
