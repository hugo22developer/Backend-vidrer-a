"""add simulation prompt to products

Revision ID: 0002_add_simulation_prompt
Revises: 0001_initial
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_add_simulation_prompt"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("simulation_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "simulation_prompt")