"""add sprint 5 teacher analytics fields and indexes

Revision ID: 97f13bbbd928
Revises: 40632c6ed9a5
Create Date: 2026-08-02 16:07:17.756296
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "97f13bbbd928"
down_revision: Union[str, Sequence[str], None] = "40632c6ed9a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply Sprint 5 teacher analytics schema changes."""

    op.alter_column(
        "attempts",
        "selected_language",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
    )

    op.create_index(
        op.f("ix_attempts_created_at"),
        "attempts",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_language_created_at",
        "attempts",
        ["selected_language", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_problem_created_at",
        "attempts",
        ["problem_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attempts_selected_language"),
        "attempts",
        ["selected_language"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_student_created_at",
        "attempts",
        ["student_alias_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_student_problem_created_at",
        "attempts",
        ["student_alias_id", "problem_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "diagnoses",
        sa.Column("decision_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "next_action",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'no_action'"),
        ),
    )

    # Protect the migration from legacy rows containing NULL confidence.
    op.execute(
        sa.text(
            "UPDATE diagnoses "
            "SET confidence = 0.0 "
            "WHERE confidence IS NULL"
        )
    )

    op.alter_column(
        "diagnoses",
        "confidence",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
    )
    op.alter_column(
        "diagnoses",
        "model_version",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=80),
        existing_nullable=False,
    )

    op.create_index(
        op.f("ix_diagnoses_created_at"),
        "diagnoses",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_diagnoses_misconception_created_at",
        "diagnoses",
        ["primary_misconception_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnoses_model_version"),
        "diagnoses",
        ["model_version"],
        unique=False,
    )
    op.create_index(
        "ix_diagnoses_model_version_created_at",
        "diagnoses",
        ["model_version", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnoses_next_action"),
        "diagnoses",
        ["next_action"],
        unique=False,
    )
    op.create_index(
        "ix_diagnoses_next_action_created_at",
        "diagnoses",
        ["next_action", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_diagnoses_state_created_at",
        "diagnoses",
        ["state", "created_at"],
        unique=False,
    )

    op.add_column(
        "diagnosis_alternatives",
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_diagnosis_alternatives_created_at",
        "diagnosis_alternatives",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_diagnosis_alternatives_diagnosis_confidence",
        "diagnosis_alternatives",
        ["diagnosis_id", "confidence"],
        unique=False,
    )
    op.create_index(
        "ix_diagnosis_alternatives_misconception_created_at",
        "diagnosis_alternatives",
        ["misconception_id", "created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_diagnosis_evidence_created_at"),
        "diagnosis_evidence",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_diagnosis_evidence_diagnosis_created_at",
        "diagnosis_evidence",
        ["diagnosis_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnosis_evidence_evidence_type"),
        "diagnosis_evidence",
        ["evidence_type"],
        unique=False,
    )
    op.create_index(
        "ix_diagnosis_evidence_rule_created_at",
        "diagnosis_evidence",
        ["rule_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnosis_evidence_rule_id"),
        "diagnosis_evidence",
        ["rule_id"],
        unique=False,
    )
    op.create_index(
        "ix_diagnosis_evidence_type_created_at",
        "diagnosis_evidence",
        ["evidence_type", "created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_misconceptions_active"),
        "misconceptions",
        ["active"],
        unique=False,
    )
    op.create_index(
        "ix_misconceptions_active_created_at",
        "misconceptions",
        ["active", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_misconceptions_active_topic",
        "misconceptions",
        ["active", "topic"],
        unique=False,
    )
    op.create_index(
        op.f("ix_misconceptions_created_at"),
        "misconceptions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_misconceptions_name"),
        "misconceptions",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_misconceptions_topic"),
        "misconceptions",
        ["topic"],
        unique=False,
    )
    op.create_index(
        "ix_misconceptions_topic_created_at",
        "misconceptions",
        ["topic", "created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_problem_misconceptions_created_at"),
        "problem_misconceptions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_problem_misconceptions_misconception_created_at",
        "problem_misconceptions",
        ["misconception_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_problem_misconceptions_problem_created_at",
        "problem_misconceptions",
        ["problem_id", "created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_problems_active"),
        "problems",
        ["active"],
        unique=False,
    )
    op.create_index(
        "ix_problems_active_created_at",
        "problems",
        ["active", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_problems_active_difficulty",
        "problems",
        ["active", "difficulty"],
        unique=False,
    )
    op.create_index(
        "ix_problems_active_topic",
        "problems",
        ["active", "topic"],
        unique=False,
    )
    op.create_index(
        op.f("ix_problems_created_at"),
        "problems",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_problems_difficulty"),
        "problems",
        ["difficulty"],
        unique=False,
    )
    op.create_index(
        op.f("ix_problems_topic"),
        "problems",
        ["topic"],
        unique=False,
    )

    op.create_index(
        op.f("ix_student_aliases_alias"),
        "student_aliases",
        ["alias"],
        unique=False,
    )
    op.create_index(
        "ix_student_aliases_alias_created_at",
        "student_aliases",
        ["alias", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_student_aliases_consent_created_at",
        "student_aliases",
        ["consent_status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_aliases_consent_status"),
        "student_aliases",
        ["consent_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_aliases_created_at"),
        "student_aliases",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_users_active_created_at",
        "users",
        ["is_active", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_created_at"),
        "users",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_is_active"),
        "users",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_role"),
        "users",
        ["role"],
        unique=False,
    )
    op.create_index(
        "ix_users_role_active",
        "users",
        ["role", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_users_role_created_at",
        "users",
        ["role", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_updated_at"),
        "users",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Revert Sprint 5 teacher analytics schema changes."""

    op.drop_index(op.f("ix_users_updated_at"), table_name="users")
    op.drop_index("ix_users_role_created_at", table_name="users")
    op.drop_index("ix_users_role_active", table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_is_active"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_index("ix_users_active_created_at", table_name="users")

    op.drop_index(
        op.f("ix_student_aliases_created_at"),
        table_name="student_aliases",
    )
    op.drop_index(
        op.f("ix_student_aliases_consent_status"),
        table_name="student_aliases",
    )
    op.drop_index(
        "ix_student_aliases_consent_created_at",
        table_name="student_aliases",
    )
    op.drop_index(
        "ix_student_aliases_alias_created_at",
        table_name="student_aliases",
    )
    op.drop_index(
        op.f("ix_student_aliases_alias"),
        table_name="student_aliases",
    )

    op.drop_index(op.f("ix_problems_topic"), table_name="problems")
    op.drop_index(op.f("ix_problems_difficulty"), table_name="problems")
    op.drop_index(op.f("ix_problems_created_at"), table_name="problems")
    op.drop_index("ix_problems_active_topic", table_name="problems")
    op.drop_index("ix_problems_active_difficulty", table_name="problems")
    op.drop_index("ix_problems_active_created_at", table_name="problems")
    op.drop_index(op.f("ix_problems_active"), table_name="problems")

    op.drop_index(
        "ix_problem_misconceptions_problem_created_at",
        table_name="problem_misconceptions",
    )
    op.drop_index(
        "ix_problem_misconceptions_misconception_created_at",
        table_name="problem_misconceptions",
    )
    op.drop_index(
        op.f("ix_problem_misconceptions_created_at"),
        table_name="problem_misconceptions",
    )

    op.drop_index(
        "ix_misconceptions_topic_created_at",
        table_name="misconceptions",
    )
    op.drop_index(
        op.f("ix_misconceptions_topic"),
        table_name="misconceptions",
    )
    op.drop_index(
        op.f("ix_misconceptions_name"),
        table_name="misconceptions",
    )
    op.drop_index(
        op.f("ix_misconceptions_created_at"),
        table_name="misconceptions",
    )
    op.drop_index(
        "ix_misconceptions_active_topic",
        table_name="misconceptions",
    )
    op.drop_index(
        "ix_misconceptions_active_created_at",
        table_name="misconceptions",
    )
    op.drop_index(
        op.f("ix_misconceptions_active"),
        table_name="misconceptions",
    )

    op.drop_index(
        "ix_diagnosis_evidence_type_created_at",
        table_name="diagnosis_evidence",
    )
    op.drop_index(
        op.f("ix_diagnosis_evidence_rule_id"),
        table_name="diagnosis_evidence",
    )
    op.drop_index(
        "ix_diagnosis_evidence_rule_created_at",
        table_name="diagnosis_evidence",
    )
    op.drop_index(
        op.f("ix_diagnosis_evidence_evidence_type"),
        table_name="diagnosis_evidence",
    )
    op.drop_index(
        "ix_diagnosis_evidence_diagnosis_created_at",
        table_name="diagnosis_evidence",
    )
    op.drop_index(
        op.f("ix_diagnosis_evidence_created_at"),
        table_name="diagnosis_evidence",
    )

    op.drop_index(
        "ix_diagnosis_alternatives_misconception_created_at",
        table_name="diagnosis_alternatives",
    )
    op.drop_index(
        "ix_diagnosis_alternatives_diagnosis_confidence",
        table_name="diagnosis_alternatives",
    )
    op.drop_index(
        "ix_diagnosis_alternatives_created_at",
        table_name="diagnosis_alternatives",
    )
    op.drop_column("diagnosis_alternatives", "reason")

    op.drop_index("ix_diagnoses_state_created_at", table_name="diagnoses")
    op.drop_index(
        "ix_diagnoses_next_action_created_at",
        table_name="diagnoses",
    )
    op.drop_index(
        op.f("ix_diagnoses_next_action"),
        table_name="diagnoses",
    )
    op.drop_index(
        "ix_diagnoses_model_version_created_at",
        table_name="diagnoses",
    )
    op.drop_index(
        op.f("ix_diagnoses_model_version"),
        table_name="diagnoses",
    )
    op.drop_index(
        "ix_diagnoses_misconception_created_at",
        table_name="diagnoses",
    )
    op.drop_index(
        op.f("ix_diagnoses_created_at"),
        table_name="diagnoses",
    )

    op.alter_column(
        "diagnoses",
        "model_version",
        existing_type=sa.String(length=80),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    op.alter_column(
        "diagnoses",
        "confidence",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
    )
    op.drop_column("diagnoses", "next_action")
    op.drop_column("diagnoses", "decision_reason")

    op.drop_index(
        "ix_attempts_student_problem_created_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_student_created_at",
        table_name="attempts",
    )
    op.drop_index(
        op.f("ix_attempts_selected_language"),
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_problem_created_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_language_created_at",
        table_name="attempts",
    )
    op.drop_index(
        op.f("ix_attempts_created_at"),
        table_name="attempts",
    )
    op.alter_column(
        "attempts",
        "selected_language",
        existing_type=sa.String(length=30),
        type_=sa.VARCHAR(length=20),
        existing_nullable=False,
    )