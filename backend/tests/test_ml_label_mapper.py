from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.ml.label_mapper import (
    LabelMappingError,
    build_combined_class_label,
    get_misconception_class,
    get_state_class,
    is_insufficient_label,
    is_no_misconception_label,
    is_positive_misconception_label,
    is_supervised_review,
    map_teacher_review_to_label,
    map_teacher_review_to_target,
    normalize_decision,
    normalize_state,
    try_map_teacher_review_to_label,
    validate_teacher_review_for_supervision,
)
from app.models.teacher_review import TeacherReview


def make_review(
    *,
    status: str = "reviewed",
    decision: str | None = "accepted",
    final_state: str | None = "confident",
    final_misconception_id: uuid.UUID | None = None,
    override_reason: str | None = None,
    reviewed_at: datetime | None = None,
) -> TeacherReview:
    """
    Build an in-memory TeacherReview suitable for label-mapper tests.

    These tests deliberately do not use a database because label mapping
    is pure domain logic.
    """

    if (
        final_misconception_id is None
        and final_state in {"confident", "possible"}
    ):
        final_misconception_id = uuid.uuid4()

    if reviewed_at is None and status == "reviewed":
        reviewed_at = datetime.utcnow()

    review = TeacherReview(
        id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        teacher_id=uuid.uuid4(),
        system_diagnosis_id=uuid.uuid4(),
        status=status,
        decision=decision,
        final_state=final_state,
        final_misconception_id=final_misconception_id,
        override_reason=override_reason,
        teacher_note=None,
        reviewed_at=reviewed_at,
    )

    return review


def test_normalize_state_lowercases_and_trims() -> None:
    assert normalize_state(" CONFIDENT ") == "confident"
    assert normalize_state("Possible") == "possible"


def test_normalize_state_returns_none_for_blank_or_none() -> None:
    assert normalize_state(None) is None
    assert normalize_state("") is None
    assert normalize_state("   ") is None


def test_normalize_decision_lowercases_and_trims() -> None:
    assert normalize_decision(" ACCEPTED ") == "accepted"
    assert normalize_decision("Overridden") == "overridden"


def test_normalize_decision_returns_none_for_blank_or_none() -> None:
    assert normalize_decision(None) is None
    assert normalize_decision("") is None
    assert normalize_decision("   ") is None


def test_confident_review_maps_to_supervised_label() -> None:
    misconception_id = uuid.uuid4()

    review = make_review(
        final_state="confident",
        final_misconception_id=misconception_id,
    )

    label = map_teacher_review_to_label(review)

    assert label.state == "confident"
    assert label.misconception_id == str(misconception_id)
    assert label.review_decision == "accepted"
    assert label.teacher_review_id == str(review.id)
    assert label.attempt_id == str(review.attempt_id)


def test_possible_review_maps_to_supervised_label() -> None:
    misconception_id = uuid.uuid4()

    review = make_review(
        final_state="possible",
        final_misconception_id=misconception_id,
    )

    label = map_teacher_review_to_label(review)

    assert label.state == "possible"
    assert label.misconception_id == str(misconception_id)


def test_no_misconception_review_maps_without_misconception_id() -> None:
    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    label = map_teacher_review_to_label(review)

    assert label.state == "no_misconception"
    assert label.misconception_id is None


def test_insufficient_review_maps_without_misconception_id() -> None:
    review = make_review(
        final_state="insufficient",
        final_misconception_id=None,
    )

    label = map_teacher_review_to_label(review)

    assert label.state == "insufficient"
    assert label.misconception_id is None


def test_overridden_review_requires_override_reason() -> None:
    review = make_review(
        decision="overridden",
        final_state="confident",
        override_reason=None,
    )

    with pytest.raises(
        LabelMappingError,
        match="override reason",
    ):
        validate_teacher_review_for_supervision(review)


def test_overridden_review_with_blank_override_reason_is_rejected() -> None:
    review = make_review(
        decision="overridden",
        final_state="confident",
        override_reason="   ",
    )

    with pytest.raises(
        LabelMappingError,
        match="override reason",
    ):
        validate_teacher_review_for_supervision(review)


def test_overridden_review_with_reason_is_valid() -> None:
    review = make_review(
        decision="overridden",
        final_state="confident",
        override_reason=(
            "Teacher found stronger misconception evidence."
        ),
    )

    validate_teacher_review_for_supervision(review)

    assert is_supervised_review(review) is True


def test_pending_review_is_not_supervised_ground_truth() -> None:
    review = make_review(
        status="pending",
        reviewed_at=None,
    )

    assert is_supervised_review(review) is False

    with pytest.raises(
        LabelMappingError,
        match="not finalized",
    ):
        map_teacher_review_to_label(review)


def test_in_review_record_is_not_supervised_ground_truth() -> None:
    review = make_review(
        status="in_review",
        reviewed_at=None,
    )

    assert is_supervised_review(review) is False


def test_reviewed_record_requires_reviewed_at() -> None:
    review = make_review()

    review.reviewed_at = None

    with pytest.raises(
        LabelMappingError,
        match="reviewed_at",
    ):
        validate_teacher_review_for_supervision(review)


def test_reviewed_record_requires_valid_decision() -> None:
    review = make_review(
        decision=None,
    )

    with pytest.raises(
        LabelMappingError,
        match="decision",
    ):
        validate_teacher_review_for_supervision(review)


@pytest.mark.parametrize(
    "decision",
    [
        "rejected",
        "unknown",
        "approved",
    ],
)
def test_invalid_review_decisions_are_rejected(
    decision: str,
) -> None:
    review = make_review(
        decision=decision,
    )

    with pytest.raises(
        LabelMappingError,
        match="decision",
    ):
        validate_teacher_review_for_supervision(review)


@pytest.mark.parametrize(
    "state",
    [
        None,
        "",
        "unknown",
        "correct",
    ],
)
def test_invalid_final_states_are_rejected(
    state: str | None,
) -> None:
    review = make_review(
        final_state=state,
        final_misconception_id=None,
    )

    with pytest.raises(
        LabelMappingError,
        match="valid final diagnosis state",
    ):
        validate_teacher_review_for_supervision(review)


@pytest.mark.parametrize(
    "state",
    [
        "confident",
        "possible",
    ],
)
def test_misconception_states_require_misconception_id(
    state: str,
) -> None:
    review = make_review(
        final_state=state,
    )

    review.final_misconception_id = None

    with pytest.raises(
        LabelMappingError,
        match="requires a final misconception",
    ):
        validate_teacher_review_for_supervision(review)


@pytest.mark.parametrize(
    "state",
    [
        "insufficient",
        "no_misconception",
    ],
)
def test_non_misconception_states_reject_misconception_id(
    state: str,
) -> None:
    review = make_review(
        final_state=state,
        final_misconception_id=None,
    )

    review.final_misconception_id = uuid.uuid4()

    with pytest.raises(
        LabelMappingError,
        match="must not contain",
    ):
        validate_teacher_review_for_supervision(review)


def test_is_supervised_review_returns_false_for_none() -> None:
    assert is_supervised_review(None) is False


def test_try_map_returns_none_for_none_review() -> None:
    assert try_map_teacher_review_to_label(None) is None


def test_try_map_returns_none_for_invalid_review() -> None:
    review = make_review(
        status="pending",
        reviewed_at=None,
    )

    result = try_map_teacher_review_to_label(review)

    assert result is None


def test_try_map_returns_label_for_valid_review() -> None:
    review = make_review()

    result = try_map_teacher_review_to_label(review)

    assert result is not None
    assert result.state == "confident"


def test_map_teacher_review_to_target_returns_compact_target() -> None:
    misconception_id = uuid.uuid4()

    review = make_review(
        final_state="possible",
        final_misconception_id=misconception_id,
    )

    target = map_teacher_review_to_target(review)

    assert target.state_label == "possible"
    assert target.misconception_label == str(misconception_id)


def test_supervised_label_to_dict() -> None:
    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    label = map_teacher_review_to_label(review)

    payload = label.to_dict()

    assert payload == {
        "state": "no_misconception",
        "misconception_id": None,
        "review_decision": "accepted",
        "teacher_review_id": str(review.id),
        "attempt_id": str(review.attempt_id),
    }


def test_classification_target_to_dict() -> None:
    review = make_review(
        final_state="insufficient",
        final_misconception_id=None,
    )

    target = map_teacher_review_to_target(review)

    assert target.to_dict() == {
        "state_label": "insufficient",
        "misconception_label": None,
    }


def test_get_state_class_returns_teacher_reviewed_state() -> None:
    review = make_review(
        final_state="possible",
    )

    assert get_state_class(review) == "possible"


def test_get_misconception_class_returns_uuid_string() -> None:
    misconception_id = uuid.uuid4()

    review = make_review(
        final_state="confident",
        final_misconception_id=misconception_id,
    )

    assert (
        get_misconception_class(review)
        == str(misconception_id)
    )


def test_get_misconception_class_returns_none_for_no_misconception() -> None:
    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    assert get_misconception_class(review) is None


def test_positive_misconception_label_for_confident_review() -> None:
    review = make_review(
        final_state="confident",
    )

    assert is_positive_misconception_label(review) is True


def test_positive_misconception_label_for_possible_review() -> None:
    review = make_review(
        final_state="possible",
    )

    assert is_positive_misconception_label(review) is True


def test_no_misconception_is_not_positive_misconception_label() -> None:
    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    assert is_positive_misconception_label(review) is False


def test_is_no_misconception_label() -> None:
    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    assert is_no_misconception_label(review) is True
    assert is_insufficient_label(review) is False


def test_is_insufficient_label() -> None:
    review = make_review(
        final_state="insufficient",
        final_misconception_id=None,
    )

    assert is_insufficient_label(review) is True
    assert is_no_misconception_label(review) is False


def test_combined_class_label_for_no_misconception() -> None:
    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    assert (
        build_combined_class_label(review)
        == "no_misconception"
    )


def test_combined_class_label_for_insufficient() -> None:
    review = make_review(
        final_state="insufficient",
        final_misconception_id=None,
    )

    assert (
        build_combined_class_label(review)
        == "insufficient"
    )


def test_combined_class_label_for_confident_misconception() -> None:
    misconception_id = uuid.uuid4()

    review = make_review(
        final_state="confident",
        final_misconception_id=misconception_id,
    )

    assert (
        build_combined_class_label(review)
        == f"confident:{misconception_id}"
    )


def test_combined_class_label_for_possible_misconception() -> None:
    misconception_id = uuid.uuid4()

    review = make_review(
        final_state="possible",
        final_misconception_id=misconception_id,
    )

    assert (
        build_combined_class_label(review)
        == f"possible:{misconception_id}"
    )


def test_mapper_uses_teacher_final_state_not_system_diagnosis() -> None:
    """
    Critical Sprint 11 anti-leakage test.

    system_diagnosis_id may point to an automated diagnosis, but the
    supervised target must come only from teacher-reviewed final fields.
    """

    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    review.system_diagnosis_id = uuid.uuid4()

    label = map_teacher_review_to_label(review)

    assert label.state == "no_misconception"
    assert label.misconception_id is None


def test_mapper_does_not_require_system_diagnosis_id() -> None:
    """
    Ground truth remains valid even if the referenced automated diagnosis
    was removed or is unavailable.
    """

    review = make_review(
        final_state="no_misconception",
        final_misconception_id=None,
    )

    review.system_diagnosis_id = None

    label = map_teacher_review_to_label(review)

    assert label.state == "no_misconception"


def test_accepted_review_does_not_require_override_reason() -> None:
    review = make_review(
        decision="accepted",
        override_reason=None,
    )

    validate_teacher_review_for_supervision(review)

    assert is_supervised_review(review) is True