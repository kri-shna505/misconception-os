from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TeacherReview(Base):
    """
    Stores the teacher's review decision for one student attempt.

    The original system diagnosis remains unchanged. Any teacher
    acceptance, correction, or override is stored separately here so
    that the automated result and the human-reviewed result remain
    independently traceable.

    Sprint 11 ML / research role
    ----------------------------
    A completed teacher review is the preferred source of supervised
    ground-truth labels for ML training and evaluation.

    The automated diagnosis MUST NOT automatically become the training
    label merely because a TeacherReview row exists.

    A review is considered usable as a supervised label only when:

    - status == "reviewed";
    - decision is "accepted" or "overridden";
    - final_state is populated;
    - final_state / final_misconception_id are logically consistent;
    - reviewed_at is populated.

    For confident/possible outcomes, final_misconception_id must exist.

    For insufficient/no_misconception outcomes,
    final_misconception_id must be NULL.

    This keeps teacher-reviewed ground truth separate from rule, ML,
    and hybrid predictions and prevents label leakage during Sprint 11
    dataset construction.
    """

    __tablename__ = "teacher_reviews"

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            name="uq_teacher_reviews_attempt_id",
        ),

        # --------------------------------------------------------------
        # Status / decision validation
        # --------------------------------------------------------------

        CheckConstraint(
            (
                "status IN ("
                "'pending', "
                "'in_review', "
                "'reviewed'"
                ")"
            ),
            name="ck_teacher_reviews_valid_status",
        ),

        CheckConstraint(
            (
                "decision IS NULL OR decision IN ("
                "'accepted', "
                "'overridden'"
                ")"
            ),
            name="ck_teacher_reviews_valid_decision",
        ),

        CheckConstraint(
            (
                "final_state IS NULL OR final_state IN ("
                "'confident', "
                "'possible', "
                "'insufficient', "
                "'no_misconception'"
                ")"
            ),
            name="ck_teacher_reviews_valid_final_state",
        ),

        # --------------------------------------------------------------
        # Sprint 11 label-integrity constraints
        # --------------------------------------------------------------

        # A finalized review must contain the information required to
        # construct a human-reviewed label.
        CheckConstraint(
            (
                "status <> 'reviewed' "
                "OR ("
                "decision IS NOT NULL "
                "AND final_state IS NOT NULL "
                "AND reviewed_at IS NOT NULL"
                ")"
            ),
            name="ck_teacher_reviews_reviewed_requires_final_fields",
        ),

        # A review that has not been finalized must not carry reviewed_at.
        CheckConstraint(
            (
                "status = 'reviewed' "
                "OR reviewed_at IS NULL"
            ),
            name="ck_teacher_reviews_reviewed_at_consistency",
        ),

        # Misconception-bearing states require a misconception ID.
        # Non-misconception states must not have one.
        CheckConstraint(
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
            name="ck_teacher_reviews_state_misconception_consistency",
        ),

        # An override should explain why the automated diagnosis changed.
        CheckConstraint(
            (
                "decision <> 'overridden' "
                "OR ("
                "override_reason IS NOT NULL "
                "AND length(trim(override_reason)) > 0"
                ")"
            ),
            name="ck_teacher_reviews_override_requires_reason",
        ),

        # --------------------------------------------------------------
        # Existing indexes
        # --------------------------------------------------------------

        Index(
            "ix_teacher_reviews_status_created_at",
            "status",
            "created_at",
        ),

        Index(
            "ix_teacher_reviews_teacher_status",
            "teacher_id",
            "status",
        ),

        Index(
            "ix_teacher_reviews_reviewed_at",
            "reviewed_at",
        ),

        Index(
            "ix_teacher_reviews_final_misconception",
            "final_misconception_id",
        ),

        # --------------------------------------------------------------
        # Sprint 11 dataset / evaluation indexes
        # --------------------------------------------------------------

        Index(
            "ix_teacher_reviews_status_final_state",
            "status",
            "final_state",
        ),

        Index(
            "ix_teacher_reviews_decision_reviewed_at",
            "decision",
            "reviewed_at",
        ),

        Index(
            "ix_teacher_reviews_final_state_misconception",
            "final_state",
            "final_misconception_id",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "attempts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Automated diagnosis being reviewed
    # ------------------------------------------------------------------

    system_diagnosis_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "diagnoses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Review lifecycle
    # ------------------------------------------------------------------

    status = Column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    decision = Column(
        String(30),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Human-reviewed final diagnosis
    # ------------------------------------------------------------------

    final_state = Column(
        String(30),
        nullable=True,
        index=True,
    )

    final_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    override_reason = Column(
        Text,
        nullable=True,
    )

    teacher_note = Column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    reviewed_at = Column(
        DateTime,
        nullable=True,
        index=True,
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

    # ------------------------------------------------------------------
    # Review lifecycle helpers
    # ------------------------------------------------------------------

    def mark_in_review(self) -> None:
        """
        Move a pending review into draft/in-review state.

        A draft/in-review record is not considered ML ground truth.
        """

        self.status = "in_review"
        self.reviewed_at = None

    def finalize(self) -> None:
        """
        Validate and mark the review as completed.

        A finalized review becomes eligible for Sprint 11 supervised
        dataset export.
        """

        self._validate_final_review()

        self.status = "reviewed"
        self.reviewed_at = datetime.utcnow()

    def reopen(self) -> None:
        """
        Reopen a finalized review for editing.

        Once reopened, the review must no longer be treated as a stable
        supervised label until it is finalized again.
        """

        self.status = "in_review"
        self.reviewed_at = None

    # ------------------------------------------------------------------
    # Sprint 11 validation
    # ------------------------------------------------------------------

    def _validate_final_review(self) -> None:
        """
        Validate the fields required for a trustworthy human-reviewed
        diagnosis before finalization.

        This mirrors the important database constraints at the Python
        domain layer so invalid reviews fail before database commit.
        """

        if self.decision not in {"accepted", "overridden"}:
            raise ValueError(
                "A finalized teacher review requires decision "
                "'accepted' or 'overridden'."
            )

        if self.final_state not in {
            "confident",
            "possible",
            "insufficient",
            "no_misconception",
        }:
            raise ValueError(
                "A finalized teacher review requires a valid final_state."
            )

        if self.final_state in {"confident", "possible"}:
            if self.final_misconception_id is None:
                raise ValueError(
                    "final_misconception_id is required for confident "
                    "or possible teacher-reviewed outcomes."
                )

        if self.final_state in {
            "insufficient",
            "no_misconception",
        }:
            if self.final_misconception_id is not None:
                raise ValueError(
                    "final_misconception_id must be empty for "
                    "insufficient or no_misconception outcomes."
                )

        if self.decision == "overridden":
            if not (self.override_reason or "").strip():
                raise ValueError(
                    "override_reason is required when the teacher "
                    "overrides the automated diagnosis."
                )

    # ------------------------------------------------------------------
    # Sprint 11 dataset / label helpers
    # ------------------------------------------------------------------

    @property
    def is_finalized(self) -> bool:
        """
        Return True when the teacher review has been finalized.
        """

        return (
            self.status == "reviewed"
            and self.reviewed_at is not None
        )

    @property
    def is_supervised_label_ready(self) -> bool:
        """
        Return True only when this review can safely provide a supervised
        ML training/evaluation label.

        This property intentionally does not use the automated diagnosis.
        The teacher-reviewed result is the label.
        """

        if not self.is_finalized:
            return False

        if self.decision not in {
            "accepted",
            "overridden",
        }:
            return False

        if self.final_state not in {
            "confident",
            "possible",
            "insufficient",
            "no_misconception",
        }:
            return False

        if self.final_state in {
            "confident",
            "possible",
        }:
            return self.final_misconception_id is not None

        return self.final_misconception_id is None

    @property
    def supervised_state_label(self) -> str | None:
        """
        Return the teacher-reviewed diagnostic-state label.

        Returns None when the review is not suitable for supervised
        training/evaluation.
        """

        if not self.is_supervised_label_ready:
            return None

        return self.final_state

    @property
    def supervised_misconception_label(self) -> str | None:
        """
        Return the teacher-reviewed misconception UUID as a string.

        no_misconception and insufficient outcomes intentionally return
        None because those states do not identify a misconception.
        """

        if not self.is_supervised_label_ready:
            return None

        if self.final_misconception_id is None:
            return None

        return str(self.final_misconception_id)

    @property
    def was_system_diagnosis_accepted(self) -> bool:
        """
        Return True when the teacher explicitly accepted the automated
        diagnosis.
        """

        return (
            self.is_finalized
            and self.decision == "accepted"
        )

    @property
    def was_system_diagnosis_overridden(self) -> bool:
        """
        Return True when the teacher explicitly corrected/overrode the
        automated diagnosis.
        """

        return (
            self.is_finalized
            and self.decision == "overridden"
        )

    def to_supervised_label(self) -> dict[str, str | None] | None:
        """
        Return the human-reviewed label representation used by the
        Sprint 11 dataset builder.

        The automated system diagnosis is deliberately excluded from
        the label itself to avoid target leakage.

        Returns None for pending/in-review/incomplete reviews.
        """

        if not self.is_supervised_label_ready:
            return None

        return {
            "state": self.supervised_state_label,
            "misconception_id": self.supervised_misconception_label,
            "review_decision": self.decision,
        }

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<TeacherReview("
            f"id={self.id}, "
            f"attempt_id={self.attempt_id}, "
            f"teacher_id={self.teacher_id}, "
            f"system_diagnosis_id={self.system_diagnosis_id}, "
            f"status={self.status!r}, "
            f"decision={self.decision!r}, "
            f"final_state={self.final_state!r}, "
            f"final_misconception_id={self.final_misconception_id}"
            f")>"
        )