from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.models.teacher_review import TeacherReview


VALID_DIAGNOSIS_STATES: Final[frozenset[str]] = frozenset(
    {
        "confident",
        "possible",
        "insufficient",
        "no_misconception",
    }
)

MISCONCEPTION_REQUIRED_STATES: Final[frozenset[str]] = frozenset(
    {
        "confident",
        "possible",
    }
)

MISCONCEPTION_FORBIDDEN_STATES: Final[frozenset[str]] = frozenset(
    {
        "insufficient",
        "no_misconception",
    }
)

VALID_REVIEW_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "accepted",
        "overridden",
    }
)


class LabelMappingError(ValueError):
    """
    Raised when a teacher review cannot safely be converted into a
    supervised-learning label.
    """


@dataclass(frozen=True, slots=True)
class SupervisedDiagnosisLabel:
    """
    Canonical supervised-learning label derived from a finalized
    teacher review.

    ``state`` represents the teacher-reviewed diagnosis state.

    ``misconception_id`` is populated only for misconception-bearing
    outcomes such as ``confident`` and ``possible``.

    ``review_decision`` records whether the teacher accepted the
    automated diagnosis or overrode it.

    ``teacher_review_id`` and ``attempt_id`` provide traceability back
    to the source review and student attempt.
    """

    state: str
    misconception_id: str | None
    review_decision: str
    teacher_review_id: str
    attempt_id: str

    def to_dict(self) -> dict[str, str | None]:
        """
        Return a serialization-safe dictionary representation.
        """

        return {
            "state": self.state,
            "misconception_id": self.misconception_id,
            "review_decision": self.review_decision,
            "teacher_review_id": self.teacher_review_id,
            "attempt_id": self.attempt_id,
        }


@dataclass(frozen=True, slots=True)
class ClassificationTarget:
    """
    Compact target representation used by ML training code.

    ``state_label`` is always present.

    ``misconception_label`` is present only when the final teacher
    review identifies a supported misconception.
    """

    state_label: str
    misconception_label: str | None

    def to_dict(self) -> dict[str, str | None]:
        """
        Return the classification target as a plain dictionary.
        """

        return {
            "state_label": self.state_label,
            "misconception_label": self.misconception_label,
        }


def normalize_state(value: str | None) -> str | None:
    """
    Normalize a diagnosis-state string.

    Returns None when the input is None or blank.
    """

    if value is None:
        return None

    normalized = value.strip().lower()

    return normalized or None


def normalize_decision(value: str | None) -> str | None:
    """
    Normalize a teacher-review decision string.

    Returns None when the input is None or blank.
    """

    if value is None:
        return None

    normalized = value.strip().lower()

    return normalized or None


def validate_teacher_review_for_supervision(
    review: TeacherReview,
) -> None:
    """
    Validate that a TeacherReview is safe to use as ML ground truth.

    A supervised label requires:

    - finalized review status;
    - reviewed_at timestamp;
    - accepted or overridden teacher decision;
    - valid final diagnosis state;
    - state/misconception consistency;
    - an override reason when the teacher changed the diagnosis.

    The automated/system diagnosis is deliberately ignored as a label.
    """

    if review is None:
        raise LabelMappingError(
            "Teacher review is required."
        )

    if review.status != "reviewed":
        raise LabelMappingError(
            "Teacher review is not finalized."
        )

    if review.reviewed_at is None:
        raise LabelMappingError(
            "Finalized teacher review requires reviewed_at."
        )

    decision = normalize_decision(
        review.decision
    )

    if decision not in VALID_REVIEW_DECISIONS:
        raise LabelMappingError(
            "Teacher review must have decision "
            "'accepted' or 'overridden'."
        )

    state = normalize_state(
        review.final_state
    )

    if state not in VALID_DIAGNOSIS_STATES:
        raise LabelMappingError(
            "Teacher review has no valid final diagnosis state."
        )

    if state in MISCONCEPTION_REQUIRED_STATES:
        if review.final_misconception_id is None:
            raise LabelMappingError(
                "Teacher review requires a final misconception "
                "for confident or possible outcomes."
            )

    if state in MISCONCEPTION_FORBIDDEN_STATES:
        if review.final_misconception_id is not None:
            raise LabelMappingError(
                "Teacher review must not contain a final "
                "misconception for insufficient or "
                "no_misconception outcomes."
            )

    if decision == "overridden":
        override_reason = (
            review.override_reason or ""
        ).strip()

        if not override_reason:
            raise LabelMappingError(
                "Overridden teacher review requires "
                "an override reason."
            )


def is_supervised_review(
    review: TeacherReview | None,
) -> bool:
    """
    Return True when the review can safely provide ML ground truth.

    Invalid reviews return False rather than raising.
    """

    if review is None:
        return False

    try:
        validate_teacher_review_for_supervision(
            review
        )
    except LabelMappingError:
        return False

    return True


def map_teacher_review_to_label(
    review: TeacherReview,
) -> SupervisedDiagnosisLabel:
    """
    Convert one finalized TeacherReview into the canonical supervised
    label used by the Sprint 11 ML pipeline.

    This function never derives the target from system_diagnosis_id,
    Diagnosis.state, rule_score, ml_score, or hybrid_score.

    Teacher-reviewed fields are the ground truth.
    """

    validate_teacher_review_for_supervision(
        review
    )

    state = normalize_state(
        review.final_state
    )

    decision = normalize_decision(
        review.decision
    )

    # Validation above guarantees both values are populated and valid.
    assert state is not None
    assert decision is not None

    misconception_id = (
        str(review.final_misconception_id)
        if review.final_misconception_id is not None
        else None
    )

    return SupervisedDiagnosisLabel(
        state=state,
        misconception_id=misconception_id,
        review_decision=decision,
        teacher_review_id=str(review.id),
        attempt_id=str(review.attempt_id),
    )


def map_teacher_review_to_target(
    review: TeacherReview,
) -> ClassificationTarget:
    """
    Convert a finalized teacher review into a compact ML target.

    This representation is convenient for baseline classifiers and
    evaluation code.
    """

    label = map_teacher_review_to_label(
        review
    )

    return ClassificationTarget(
        state_label=label.state,
        misconception_label=label.misconception_id,
    )


def try_map_teacher_review_to_label(
    review: TeacherReview | None,
) -> SupervisedDiagnosisLabel | None:
    """
    Safely map a review to a supervised label.

    Returns None for pending, incomplete, or inconsistent reviews.

    Dataset-export code should normally use this helper when scanning
    many database rows so one unusable review does not abort the
    complete export.
    """

    if review is None:
        return None

    try:
        return map_teacher_review_to_label(
            review
        )
    except LabelMappingError:
        return None


def get_state_class(
    review: TeacherReview,
) -> str:
    """
    Return the supervised diagnosis-state class.
    """

    label = map_teacher_review_to_label(
        review
    )

    return label.state


def get_misconception_class(
    review: TeacherReview,
) -> str | None:
    """
    Return the supervised misconception class.

    Returns None for insufficient and no_misconception outcomes.
    """

    label = map_teacher_review_to_label(
        review
    )

    return label.misconception_id


def is_positive_misconception_label(
    review: TeacherReview,
) -> bool:
    """
    Return True when the teacher-reviewed outcome identifies a
    misconception.

    Both confident and possible states count as positive
    misconception-bearing labels.
    """

    label = map_teacher_review_to_label(
        review
    )

    return (
        label.state
        in MISCONCEPTION_REQUIRED_STATES
        and label.misconception_id is not None
    )


def is_no_misconception_label(
    review: TeacherReview,
) -> bool:
    """
    Return True when the teacher explicitly finalized the attempt as
    having no supported misconception.
    """

    label = map_teacher_review_to_label(
        review
    )

    return (
        label.state
        == "no_misconception"
        and label.misconception_id is None
    )


def is_insufficient_label(
    review: TeacherReview,
) -> bool:
    """
    Return True when the teacher finalized the evidence as
    insufficient for a misconception classification.
    """

    label = map_teacher_review_to_label(
        review
    )

    return (
        label.state == "insufficient"
        and label.misconception_id is None
    )


def build_combined_class_label(
    review: TeacherReview,
) -> str:
    """
    Build a stable combined target string.

    Examples:

        no_misconception

        insufficient

        confident:<misconception-uuid>

        possible:<misconception-uuid>

    This can be useful for simple single-output baseline experiments.

    More advanced models should normally keep state and misconception
    prediction as separate targets.
    """

    label = map_teacher_review_to_label(
        review
    )

    if label.misconception_id is None:
        return label.state

    return (
        f"{label.state}:"
        f"{label.misconception_id}"
    )


__all__ = [
    "ClassificationTarget",
    "LabelMappingError",
    "MISCONCEPTION_FORBIDDEN_STATES",
    "MISCONCEPTION_REQUIRED_STATES",
    "SupervisedDiagnosisLabel",
    "VALID_DIAGNOSIS_STATES",
    "VALID_REVIEW_DECISIONS",
    "build_combined_class_label",
    "get_misconception_class",
    "get_state_class",
    "is_insufficient_label",
    "is_no_misconception_label",
    "is_positive_misconception_label",
    "is_supervised_review",
    "map_teacher_review_to_label",
    "map_teacher_review_to_target",
    "normalize_decision",
    "normalize_state",
    "try_map_teacher_review_to_label",
    "validate_teacher_review_for_supervision",
]