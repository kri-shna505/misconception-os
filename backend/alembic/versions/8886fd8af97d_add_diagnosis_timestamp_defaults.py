"""add diagnosis timestamp defaults

Revision ID: 8886fd8af97d
Revises: fd71c245bc0d
Create Date: 2026-08-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8886fd8af97d"
down_revision = "fd71c245bc0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add database-side timestamp defaults for diagnosis inserts.

    The application normally supplies timestamps through SQLAlchemy model
    defaults. The database defaults protect inserts that omit these columns
    and prevent NOT NULL violations.
    """

    op.alter_column(
        "diagnoses",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    op.alter_column(
        "diagnoses",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    """
    Remove the database-side timestamp defaults.
    """

    op.alter_column(
        "diagnoses",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )

    op.alter_column(
        "diagnoses",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )