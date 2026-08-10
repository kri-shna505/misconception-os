"""add_resulting_diagnosis_to_diagnostic_responses

Revision ID: 01ab57a89c8a
Revises: 8886fd8af97d
Create Date: 2026-08-07 00:50:07.761974

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "01ab57a89c8a"
down_revision: Union[str, Sequence[str], None] = "8886fd8af97d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add the follow-up diagnosis link used by Sprint 9 diagnostic
    question re-evaluation.

    The column is nullable because existing and unevaluated diagnostic
    responses do not yet have a resulting diagnosis.
    """

    op.add_column(
        "diagnostic_responses",
        sa.Column(
            "resulting_diagnosis_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_diagnostic_responses_resulting_diagnosis_id_diagnoses",
        "diagnostic_responses",
        "diagnoses",
        ["resulting_diagnosis_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_unique_constraint(
        "uq_diagnostic_responses_resulting_diagnosis",
        "diagnostic_responses",
        ["resulting_diagnosis_id"],
    )

    op.create_index(
        "ix_diagnostic_responses_resulting_diagnosis_id",
        "diagnostic_responses",
        ["resulting_diagnosis_id"],
        unique=False,
    )

    op.create_index(
        "ix_diagnostic_responses_resulting_diagnosis_created_at",
        "diagnostic_responses",
        [
            "resulting_diagnosis_id",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    """
    Remove the follow-up diagnosis link and its supporting database objects.
    """

    op.drop_index(
        "ix_diagnostic_responses_resulting_diagnosis_created_at",
        table_name="diagnostic_responses",
    )

    op.drop_index(
        "ix_diagnostic_responses_resulting_diagnosis_id",
        table_name="diagnostic_responses",
    )

    op.drop_constraint(
        "uq_diagnostic_responses_resulting_diagnosis",
        "diagnostic_responses",
        type_="unique",
    )

    op.drop_constraint(
        "fk_diagnostic_responses_resulting_diagnosis_id_diagnoses",
        "diagnostic_responses",
        type_="foreignkey",
    )

    op.drop_column(
        "diagnostic_responses",
        "resulting_diagnosis_id",
    )