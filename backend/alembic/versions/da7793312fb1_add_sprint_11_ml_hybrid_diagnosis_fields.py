"""add sprint 11 ml hybrid diagnosis fields

Revision ID: da7793312fb1
Revises: 3a7c9d10e2f4
Create Date: 2026-08-14 00:16:41.507664

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "da7793312fb1"
down_revision: Union[str, Sequence[str], None] = "3a7c9d10e2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add Sprint 11 ML/hybrid diagnosis persistence and
    teacher-review label-integrity support.
    """

    # ------------------------------------------------------------------
    # Diagnosis: Sprint 11 ML / hybrid fields
    # ------------------------------------------------------------------

    op.add_column(
        "diagnoses",
        sa.Column(
            "ml_score",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "diagnoses",
        sa.Column(
            "hybrid_score",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "diagnoses",
        sa.Column(
            "prediction_source",
            sa.String(length=20),
            nullable=False,
            server_default="rule",
        ),
    )

    op.add_column(
        "diagnoses",
        sa.Column(
            "feature_version",
            sa.String(length=80),
            nullable=True,
        ),
    )

    op.add_column(
        "diagnoses",
        sa.Column(
            "calibration_version",
            sa.String(length=80),
            nullable=True,
        ),
    )

    # Current production rule engine is rule-v1.9.
    # Existing diagnosis rows are NOT rewritten; only the database
    # default for newly-created rows changes.
    op.alter_column(
        "diagnoses",
        "model_version",
        existing_type=sa.String(length=80),
        existing_nullable=False,
        server_default="rule-v1.9",
    )

    # ------------------------------------------------------------------
    # Diagnosis: score / provenance constraints
    # ------------------------------------------------------------------

    op.create_check_constraint(
        "ck_diagnoses_ml_score_range",
        "diagnoses",
        (
            "ml_score IS NULL "
            "OR (ml_score >= 0.0 AND ml_score <= 1.0)"
        ),
    )

    op.create_check_constraint(
        "ck_diagnoses_hybrid_score_range",
        "diagnoses",
        (
            "hybrid_score IS NULL "
            "OR (hybrid_score >= 0.0 AND hybrid_score <= 1.0)"
        ),
    )

    op.create_check_constraint(
        "ck_diagnoses_valid_prediction_source",
        "diagnoses",
        (
            "prediction_source IN ("
            "'rule', "
            "'ml', "
            "'hybrid'"
            ")"
        ),
    )

    op.create_check_constraint(
        "ck_diagnoses_ml_source_requires_ml_score",
        "diagnoses",
        (
            "prediction_source <> 'ml' "
            "OR ml_score IS NOT NULL"
        ),
    )

    op.create_check_constraint(
        "ck_diagnoses_hybrid_source_requires_hybrid_score",
        "diagnoses",
        (
            "prediction_source <> 'hybrid' "
            "OR hybrid_score IS NOT NULL"
        ),
    )

    # ------------------------------------------------------------------
    # Diagnosis: Sprint 11 indexes
    # ------------------------------------------------------------------

    op.create_index(
        "ix_diagnoses_prediction_source",
        "diagnoses",
        ["prediction_source"],
        unique=False,
    )

    op.create_index(
        "ix_diagnoses_prediction_source_created_at",
        "diagnoses",
        [
            "prediction_source",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_diagnoses_feature_version",
        "diagnoses",
        ["feature_version"],
        unique=False,
    )

    op.create_index(
        "ix_diagnoses_feature_version_created_at",
        "diagnoses",
        [
            "feature_version",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_diagnoses_calibration_version",
        "diagnoses",
        ["calibration_version"],
        unique=False,
    )

    op.create_index(
        "ix_diagnoses_calibration_version_created_at",
        "diagnoses",
        [
            "calibration_version",
            "created_at",
        ],
        unique=False,
    )

    # ------------------------------------------------------------------
    # TeacherReview: label-integrity constraints
    # ------------------------------------------------------------------

    op.create_check_constraint(
        "ck_teacher_reviews_reviewed_requires_final_fields",
        "teacher_reviews",
        (
            "status <> 'reviewed' "
            "OR ("
            "decision IS NOT NULL "
            "AND final_state IS NOT NULL "
            "AND reviewed_at IS NOT NULL"
            ")"
        ),
    )

    op.create_check_constraint(
        "ck_teacher_reviews_reviewed_at_consistency",
        "teacher_reviews",
        (
            "status = 'reviewed' "
            "OR reviewed_at IS NULL"
        ),
    )

    op.create_check_constraint(
        "ck_teacher_reviews_state_misconception_consistency",
        "teacher_reviews",
        (
            "final_state IS NULL "
            "OR ("
            "final_state IN ('confident', 'possible') "
            "AND final_misconception_id IS NOT NULL"
            ") "
            "OR ("
            "final_state IN ('insufficient', 'no_misconception') "
            "AND final_misconception_id IS NULL"
            ")"
        ),
    )

    op.create_check_constraint(
        "ck_teacher_reviews_override_requires_reason",
        "teacher_reviews",
        (
            "decision <> 'overridden' "
            "OR ("
            "override_reason IS NOT NULL "
            "AND length(trim(override_reason)) > 0"
            ")"
        ),
    )

    # ------------------------------------------------------------------
    # TeacherReview: indexes required by current ORM model
    # ------------------------------------------------------------------

    op.create_index(
        "ix_teacher_reviews_attempt_id",
        "teacher_reviews",
        ["attempt_id"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_created_at",
        "teacher_reviews",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_status",
        "teacher_reviews",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_teacher_id",
        "teacher_reviews",
        ["teacher_id"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_updated_at",
        "teacher_reviews",
        ["updated_at"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_final_misconception",
        "teacher_reviews",
        ["final_misconception_id"],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_decision_reviewed_at",
        "teacher_reviews",
        [
            "decision",
            "reviewed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_status_final_state",
        "teacher_reviews",
        [
            "status",
            "final_state",
        ],
        unique=False,
    )

    op.create_index(
        "ix_teacher_reviews_final_state_misconception",
        "teacher_reviews",
        [
            "final_state",
            "final_misconception_id",
        ],
        unique=False,
    )


def downgrade() -> None:
    """
    Remove Sprint 11 ML/hybrid diagnosis persistence and
    teacher-review label-integrity support.
    """

    # ------------------------------------------------------------------
    # TeacherReview indexes
    # ------------------------------------------------------------------

    op.drop_index(
        "ix_teacher_reviews_final_state_misconception",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_status_final_state",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_decision_reviewed_at",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_final_misconception",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_updated_at",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_teacher_id",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_status",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_created_at",
        table_name="teacher_reviews",
    )

    op.drop_index(
        "ix_teacher_reviews_attempt_id",
        table_name="teacher_reviews",
    )

    # ------------------------------------------------------------------
    # TeacherReview constraints
    # ------------------------------------------------------------------

    op.drop_constraint(
        "ck_teacher_reviews_override_requires_reason",
        "teacher_reviews",
        type_="check",
    )

    op.drop_constraint(
        "ck_teacher_reviews_state_misconception_consistency",
        "teacher_reviews",
        type_="check",
    )

    op.drop_constraint(
        "ck_teacher_reviews_reviewed_at_consistency",
        "teacher_reviews",
        type_="check",
    )

    op.drop_constraint(
        "ck_teacher_reviews_reviewed_requires_final_fields",
        "teacher_reviews",
        type_="check",
    )

    # ------------------------------------------------------------------
    # Diagnosis indexes
    # ------------------------------------------------------------------

    op.drop_index(
        "ix_diagnoses_calibration_version_created_at",
        table_name="diagnoses",
    )

    op.drop_index(
        "ix_diagnoses_calibration_version",
        table_name="diagnoses",
    )

    op.drop_index(
        "ix_diagnoses_feature_version_created_at",
        table_name="diagnoses",
    )

    op.drop_index(
        "ix_diagnoses_feature_version",
        table_name="diagnoses",
    )

    op.drop_index(
        "ix_diagnoses_prediction_source_created_at",
        table_name="diagnoses",
    )

    op.drop_index(
        "ix_diagnoses_prediction_source",
        table_name="diagnoses",
    )

    # ------------------------------------------------------------------
    # Diagnosis constraints
    # ------------------------------------------------------------------

    op.drop_constraint(
        "ck_diagnoses_hybrid_source_requires_hybrid_score",
        "diagnoses",
        type_="check",
    )

    op.drop_constraint(
        "ck_diagnoses_ml_source_requires_ml_score",
        "diagnoses",
        type_="check",
    )

    op.drop_constraint(
        "ck_diagnoses_valid_prediction_source",
        "diagnoses",
        type_="check",
    )

    op.drop_constraint(
        "ck_diagnoses_hybrid_score_range",
        "diagnoses",
        type_="check",
    )

    op.drop_constraint(
        "ck_diagnoses_ml_score_range",
        "diagnoses",
        type_="check",
    )

    # Restore the previous database default.
    op.alter_column(
        "diagnoses",
        "model_version",
        existing_type=sa.String(length=80),
        existing_nullable=False,
        server_default="rule-v1.4",
    )

    # ------------------------------------------------------------------
    # Diagnosis columns
    # ------------------------------------------------------------------

    op.drop_column(
        "diagnoses",
        "calibration_version",
    )

    op.drop_column(
        "diagnoses",
        "feature_version",
    )

    op.drop_column(
        "diagnoses",
        "prediction_source",
    )

    op.drop_column(
        "diagnoses",
        "hybrid_score",
    )

    op.drop_column(
        "diagnoses",
        "ml_score",
    )