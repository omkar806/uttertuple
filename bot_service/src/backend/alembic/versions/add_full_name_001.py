"""Add full_name column to users table

Revision ID: add_full_name_001
Revises:
Create Date: 2025-09-28 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_full_name_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add full_name column to users table
    op.add_column("users", sa.Column("full_name", sa.String(length=500), nullable=True))


def downgrade() -> None:
    # Remove full_name column from users table
    op.drop_column("users", "full_name")
