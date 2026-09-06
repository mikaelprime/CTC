"""recreate students table

Revision ID: 2f726266858e
Revises: 5c5f06665f0f
Create Date: 2026-07-28 02:16:20.987664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f726266858e'
down_revision: Union[str, Sequence[str], None] = '5c5f06665f0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    pass
