"""fix user timestamps

Revision ID: 9446157c86a9
Revises: e3063f1283fd
Create Date: 2026-02-08 18:14:01.734795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9446157c86a9'
down_revision: Union[str, Sequence[str], None] = 'e3063f1283fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # created_at
    op.alter_column(
        "users",
        "created_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        server_default=sa.text("NOW()"),
        existing_nullable=False,
    )

    # updated_at
    op.alter_column(
        "users",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
        server_default=sa.text("NOW()"),
        existing_nullable=False,
    )

def downgrade():
    op.alter_column(
        "users",
        "created_at",
        type_=sa.DateTime(timezone=False),
    )

    op.alter_column(
        "users",
        "updated_at",
        type_=sa.DateTime(timezone=False),
    )
