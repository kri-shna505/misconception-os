import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Attempt(Base):
    """
    Stores one pseudonymous student submission.

    Sprint 9 retry support:
    - An original attempt has parent_attempt_id=None and retry_number=0.
    - A retry points to the immediately previous attempt.
    - retry_number increases within the same student/problem attempt chain.

    Sprint 10 multimodal/language support:
    - written_reasoning, source_code, and final_answer remain core inputs.
    - speech_transcript stores the normalized transcript used by diagnosis.
    - input_language records the student's natural-language selection.
    - detected_language records the language detected by the processing layer.
    - input_modality records which student modalities were supplied.
    - speech_processing_status tracks transcript-processing state.
    - speech_audio_reference may temporarily reference uploaded audio while
      transcription is pending.
    - speech_audio_retained records whether raw audio is retained with explicit
      research consent. By default raw audio should be deleted after feature
      extraction/transcription.
    - normalized_reasoning stores language/code-switch normalized reasoning
      without overwriting the student's original written text.

    The application service must additionally verify that a retry and its
    parent belong to the same student alias and problem. That rule cannot be
    reliably enforced through a simple database CHECK constraint because it
    requires reading values from another row.
    """

    __tablename__ = "attempts"

    __table_args__ = (
        Index(
            "ix_attempts_student_created_at",
            "student_alias_id",
            "created_at",
        ),
        Index(
            "ix_attempts_problem_created_at",
            "problem_id",
            "created_at",
        ),
        Index(
            "ix_attempts_language_created_at",
            "selected_language",
            "created_at",
        ),
        Index(
            "ix_attempts_input_language_created_at",
            "input_language",
            "created_at",
        ),
        Index(
            "ix_attempts_detected_language_created_at",
            "detected_language",
            "created_at",
        ),
        Index(
            "ix_attempts_modality_created_at",
            "input_modality",
            "created_at",
        ),
        Index(
            "ix_attempts_speech_status_created_at",
            "speech_processing_status",
            "created_at",
        ),
        Index(
            "ix_attempts_student_problem_created_at",
            "student_alias_id",
            "problem_id",
            "created_at",
        ),
        Index(
            "ix_attempts_parent_created_at",
            "parent_attempt_id",
            "created_at",
        ),
        Index(
            "ix_attempts_student_problem_retry",
            "student_alias_id",
            "problem_id",
            "retry_number",
        ),
        CheckConstraint(
            (
                "response_time_seconds IS NULL "
                "OR response_time_seconds >= 0"
            ),
            name="ck_attempts_response_time_nonnegative",
        ),
        CheckConstraint(
            "retry_number >= 0",
            name="ck_attempts_retry_number_nonnegative",
        ),
        CheckConstraint(
            (
                "parent_attempt_id IS NULL "
                "OR parent_attempt_id <> id"
            ),
            name="ck_attempts_parent_not_self",
        ),
        CheckConstraint(
            (
                "(parent_attempt_id IS NULL AND retry_number = 0) "
                "OR "
                "(parent_attempt_id IS NOT NULL AND retry_number >= 1)"
            ),
            name="ck_attempts_parent_retry_consistency",
        ),
        CheckConstraint(
            (
                "speech_processing_status IN ("
                "'not_provided', "
                "'pending', "
                "'processing', "
                "'completed', "
                "'failed'"
                ")"
            ),
            name="ck_attempts_valid_speech_processing_status",
        ),
        CheckConstraint(
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
            name="ck_attempts_valid_input_modality",
        ),
        CheckConstraint(
            (
                "speech_audio_retained = FALSE "
                "OR speech_audio_reference IS NOT NULL"
            ),
            name="ck_attempts_retained_audio_requires_reference",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    student_alias_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "student_aliases.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    problem_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "problems.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    parent_attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "attempts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    retry_number = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
    )

    final_answer = Column(
        Text,
        nullable=True,
    )

    written_reasoning = Column(
        Text,
        nullable=False,
    )

    normalized_reasoning = Column(
        Text,
        nullable=True,
    )

    source_code = Column(
        Text,
        nullable=True,
    )

    speech_transcript = Column(
        Text,
        nullable=True,
    )

    speech_audio_reference = Column(
        Text,
        nullable=True,
    )

    speech_audio_retained = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    speech_processing_status = Column(
        String(30),
        nullable=False,
        default="not_provided",
        server_default="not_provided",
        index=True,
    )

    input_modality = Column(
        String(30),
        nullable=False,
        default="text",
        server_default="text",
        index=True,
    )

    input_language = Column(
        String(30),
        nullable=False,
        default="english",
        server_default="english",
        index=True,
    )

    detected_language = Column(
        String(30),
        nullable=True,
        index=True,
    )

    selected_language = Column(
        String(30),
        nullable=False,
        default="python",
        index=True,
    )

    response_time_seconds = Column(
        Integer,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )

    @property
    def is_retry(self) -> bool:
        return (
            self.parent_attempt_id is not None
            and self.retry_number > 0
        )

    @property
    def has_speech_input(self) -> bool:
        return bool(
            self.speech_transcript
            or self.speech_audio_reference
            or self.speech_processing_status
            not in {
                None,
                "not_provided",
            }
        )

    @property
    def has_code_input(self) -> bool:
        return bool(
            self.source_code
            and self.source_code.strip()
        )

    @property
    def reasoning_for_diagnosis(self) -> str:
        normalized = (
            self.normalized_reasoning
            or ""
        ).strip()

        if normalized:
            return normalized

        return (
            self.written_reasoning
            or ""
        ).strip()

    def link_to_parent(
        self,
        *,
        parent_attempt_id: uuid.UUID,
        retry_number: int,
    ) -> None:
        if parent_attempt_id == self.id:
            raise ValueError(
                "An attempt cannot use itself as its parent."
            )

        if retry_number < 1:
            raise ValueError(
                "A linked retry must have retry_number >= 1."
            )

        self.parent_attempt_id = parent_attempt_id
        self.retry_number = retry_number

    def mark_speech_pending(
        self,
        *,
        audio_reference: str,
        retain_audio: bool = False,
    ) -> None:
        normalized_reference = (
            audio_reference
            or ""
        ).strip()

        if not normalized_reference:
            raise ValueError(
                "audio_reference is required when speech processing is pending."
            )

        self.speech_audio_reference = normalized_reference
        self.speech_audio_retained = bool(
            retain_audio
        )
        self.speech_processing_status = "pending"

    def mark_speech_completed(
        self,
        *,
        transcript: str,
        delete_audio_reference: bool = True,
    ) -> None:
        normalized_transcript = (
            transcript
            or ""
        ).strip()

        if not normalized_transcript:
            raise ValueError(
                "A non-empty transcript is required to complete speech processing."
            )

        self.speech_transcript = normalized_transcript
        self.speech_processing_status = "completed"

        if (
            delete_audio_reference
            and not self.speech_audio_retained
        ):
            self.speech_audio_reference = None

    def mark_speech_failed(self) -> None:
        self.speech_processing_status = "failed"

    def __repr__(self) -> str:
        return (
            f"<Attempt("
            f"id={self.id}, "
            f"student_alias_id={self.student_alias_id}, "
            f"problem_id={self.problem_id}, "
            f"parent_attempt_id={self.parent_attempt_id}, "
            f"retry_number={self.retry_number}, "
            f"input_modality={self.input_modality!r}, "
            f"input_language={self.input_language!r}, "
            f"selected_language={self.selected_language!r}, "
            f"speech_processing_status={self.speech_processing_status!r}, "
            f"response_time_seconds={self.response_time_seconds}"
            f")>"
        )