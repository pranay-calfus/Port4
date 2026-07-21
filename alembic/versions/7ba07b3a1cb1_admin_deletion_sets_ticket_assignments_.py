"""admin deletion sets ticket assignments to null

Revision ID: 7ba07b3a1cb1
Revises: 14de25bc813f
Create Date: 2026-07-21 11:21:59.686334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ba07b3a1cb1'
down_revision: Union[str, Sequence[str], None] = '14de25bc813f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('ticket_messages_sender_id_fkey'), 'ticket_messages', type_='foreignkey')
    op.create_foreign_key(
        op.f('ticket_messages_sender_id_fkey'),
        'ticket_messages', 'users', ['sender_id'], ['id'], ondelete='SET NULL',
    )
    op.drop_constraint(op.f('tickets_assigned_admin_id_fkey'), 'tickets', type_='foreignkey')
    op.create_foreign_key(
        op.f('tickets_assigned_admin_id_fkey'),
        'tickets', 'users', ['assigned_admin_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('tickets_assigned_admin_id_fkey'), 'tickets', type_='foreignkey')
    op.create_foreign_key(
        op.f('tickets_assigned_admin_id_fkey'), 'tickets', 'users', ['assigned_admin_id'], ['id']
    )
    op.drop_constraint(op.f('ticket_messages_sender_id_fkey'), 'ticket_messages', type_='foreignkey')
    op.create_foreign_key(
        op.f('ticket_messages_sender_id_fkey'), 'ticket_messages', 'users', ['sender_id'], ['id']
    )
