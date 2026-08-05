"""add sprint 7a teacher authentication and reviews

Revision ID: bf7a91b16011
Revises: 97f13bbbd928
Create Date: 2026-08-02 19:53:56.070726
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bf7a91b16011"
down_revision: Union[str, Sequence[str], None] = "97f13bbbd928"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Sprint 7A authentication metadata and teacher review workflow."""

    op.create_table(
        "teacher_reviews",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "attempt_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "teacher_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "system_diagnosis_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "final_state",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "final_misconception_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "override_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "teacher_note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "decision IS NULL OR decision IN "
                "('accepted', 'overridden')"
            ),
            name="ck_teacher_reviews_valid_decision",
        ),
        sa.CheckConstraint(
            (
                "final_state IS NULL OR final_state IN "
                "('confident', 'possible', "
                "'insufficient', 'no_misconception')"
            ),
            name="ck_teacher_reviews_valid_final_state",
        ),
        sa.CheckConstraint(
            (
                "status IN "
                "('pending', 'in_review', 'reviewed')"
            ),
            name="ck_teacher_reviews_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["attempts.id"],
            name="fk_teacher_reviews_attempt_id_attempts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            name="fk_teacher_reviews_teacher_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["system_diagnosis_id"],
            ["diagnoses.id"],
            name="fk_teacher_reviews_system_diagnosis_id_diagnoses",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["final_misconception_id"],
            ["misconceptions.id"],
            name=(
                "fk_teacher_reviews_final_misconception_id_"
                "misconceptions"
            ),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_teacher_reviews",
        ),
        sa.UniqueConstraint(
            "attempt_id",
            name="uq_teacher_reviews_attempt_id",
        ),
    )

    op.create_index(
        "ix_teacher_reviews_status_created_at",
        "teacher_reviews",
        ["status", "created_at"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_teacher_status",
        "teacher_reviews",
        ["teacher_id", "status"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_system_diagnosis_id",
        "teacher_reviews",
        ["system_diagnosis_id"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_final_misconception_id",
        "teacher_reviews",
        ["final_misconception_id"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_final_state",
        "teacher_reviews",
        ["final_state"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_reviewed_at",
        "teacher_reviews",
        ["reviewed_at"],
        unique=False,
    )

    # Add optional user profile and authentication metadata.
    op.add_column(
        "users",
        sa.Column(
            "display_name",
            sa.String(length=120),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "last_login_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    # Existing users require a safe backfill before enforcing NOT NULL.
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE users
        SET password_changed_at = COALESCE(updated_at, created_at, NOW())
        WHERE password_changed_at IS NULL
        """
    )

    op.alter_column(
        "users",
        "password_changed_at",
        existing_type=sa.DateTime(),
        nullable=False,
    )

    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=50),
        server_default="teacher",
        existing_nullable=False,
    )

    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.create_check_constraint(
        "ck_users_valid_role",
        "users",
        "role IN ('teacher', 'admin')",
    )

    op.create_check_constraint(
        "ck_users_failed_login_attempts_non_negative",
        "users",
        "failed_login_attempts >= 0",
    )

    op.create_check_constraint(
        "ck_users_token_version_non_negative",
        "users",
        "token_version >= 0",
    )

    op.create_index(
        "ix_users_email_active",
        "users",
        ["email", "is_active"],
        unique=False,
    )

    op.create_index(
        "ix_users_last_login_at",
        "users",
        ["last_login_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Sprint 7A authentication metadata and teacher reviews."""

    op.drop_index(
        "ix_users_last_login_at",
        table_name="users",
    )

    op.drop_index(
        "ix_users_email_active",
        table_name="users",
    )

    op.drop_constraint(
        "ck_users_token_version_non_negative",
        "users",
        type_="check",
    )

    op.drop_constraint(
        "ck_users_failed_login_attempts_non_negative",
        "users",
        type_="check",
    )

    op.drop_constraint(
        "ck_users_valid_role",
        "users",
        type_="check",
    )

    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=50),
        server_default=None,
        existing_nullable=False,
    )

    op.drop_column(
        "users",
        "token_version",
    )

    op.drop_column(
        "users",
        "password_changed_at",
    )

    op.drop_column(
        "users",
        "last_login_at",
    )

    op.drop_column(
        "users",
        "failed_login_attempts",
    )

    op.drop_column(
        "users",
        "display_name",
    )

    op.drop_index(
        "ix_teacher_reviews_reviewed_at",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_final_state",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_final_misconception_id",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_system_diagnosis_id",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_teacher_status",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_status_created_at",
        table_name="teacher_reviews",
    )

    op.drop_table("teacher_reviews")