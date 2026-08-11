"""add sprint 10 multimodal attempt fields

Revision ID: 3a7c9d10e2f4
Revises: 01ab57a89c8a
Create Date: 2026-08-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a7c9d10e2f4"
down_revision: Union[str, Sequence[str], None] = "01ab57a89c8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Sprint 10 multimodal and language-processing fields to attempts."""

    op.add_column(
        "attempts",
        sa.Column("normalized_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "attempts",
        sa.Column("speech_audio_reference", sa.Text(), nullable=True),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "speech_audio_retained",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "speech_processing_status",
            sa.String(length=30),
            server_default="not_provided",
            nullable=False,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "input_modality",
            sa.String(length=30),
            server_default="text",
            nullable=False,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "input_language",
            sa.String(length=30),
            server_default="english",
            nullable=False,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "detected_language",
            sa.String(length=30),
            nullable=True,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.alter_column(
        "attempts",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )

    op.create_check_constraint(
        "ck_attempts_valid_speech_processing_status",
        "attempts",
        (
            "speech_processing_status IN ("
            "'not_provided', "
            "'pending', "
            "'processing', "
            "'completed', "
            "'failed'"
            ")"
        ),
    )

    op.create_check_constraint(
        "ck_attempts_valid_input_modality",
        "attempts",
        (
            "input_modality IN ("
            "'text', "
            "'code', "
            "'speech', "
            "'text_code', "
            "'text_speech', "
            "'code_speech', "
            "'text_code_speech'"
            ")"
        ),
    )

    op.create_check_constraint(
        "ck_attempts_retained_audio_requires_reference",
        "attempts",
        (
            "speech_audio_retained = FALSE "
            "OR speech_audio_reference IS NOT NULL"
        ),
    )

    op.create_index(
        "ix_attempts_input_language",
        "attempts",
        ["input_language"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_detected_language",
        "attempts",
        ["detected_language"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_input_modality",
        "attempts",
        ["input_modality"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_speech_processing_status",
        "attempts",
        ["speech_processing_status"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_updated_at",
        "attempts",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_input_language_created_at",
        "attempts",
        ["input_language", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_detected_language_created_at",
        "attempts",
        ["detected_language", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_modality_created_at",
        "attempts",
        ["input_modality", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_speech_status_created_at",
        "attempts",
        ["speech_processing_status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Sprint 10 multimodal and language-processing fields."""

    op.drop_index(
        "ix_attempts_speech_status_created_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_modality_created_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_detected_language_created_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_input_language_created_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_updated_at",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_speech_processing_status",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_input_modality",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_detected_language",
        table_name="attempts",
    )
    op.drop_index(
        "ix_attempts_input_language",
        table_name="attempts",
    )

    op.drop_constraint(
        "ck_attempts_retained_audio_requires_reference",
        "attempts",
        type_="check",
    )
    op.drop_constraint(
        "ck_attempts_valid_input_modality",
        "attempts",
        type_="check",
    )
    op.drop_constraint(
        "ck_attempts_valid_speech_processing_status",
        "attempts",
        type_="check",
    )

    op.drop_column("attempts", "updated_at")
    op.drop_column("attempts", "detected_language")
    op.drop_column("attempts", "input_language")
    op.drop_column("attempts", "input_modality")
    op.drop_column("attempts", "speech_processing_status")
    op.drop_column("attempts", "speech_audio_retained")
    op.drop_column("attempts", "speech_audio_reference")
    op.drop_column("attempts", "normalized_reasoning")