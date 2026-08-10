from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.diagnosis import Diagnosis
from app.models.hint_event import HintEvent
from app.models.hint_template import HintTemplate


MAX_HINT_LEVEL = 3

HINT_ELIGIBLE_STATE = "confident"
HINT_ELIGIBLE_NEXT_ACTION = "show_hint"


@dataclass(frozen=True, slots=True)
class HintDeliveryResult:
    """
    Structured result returned after revealing a progressive hint.
    """

    hint_event_id: UUID
    diagnosis_id: UUID
    attempt_id: UUID
    student_alias_id: UUID

    hint_template_id: UUID
    misconception_id: UUID

    level: int
    hint_text: str

    is_final_level: bool
    remaining_levels: int

    created_at: datetime


@dataclass(frozen=True, slots=True)
class HintProgressResult:
    """
    Current progressive-hint status for one diagnosis.
    """

    diagnosis_id: UUID
    attempt_id: UUID
    student_alias_id: UUID
    misconception_id: UUID

    revealed_levels: tuple[int, ...]
    next_level: int | None
    maximum_level: int

    completed: bool


def get_hint_progress(
    *,
    db: Session,
    diagnosis_id: UUID,
    student_alias_id: UUID,
) -> HintProgressResult:
    """
    Return progressive-hint status without revealing a new hint.

    The student must own the attempt connected to the diagnosis.
    """

    diagnosis, attempt = _get_owned_diagnosis_context(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    misconception_id = _require_hint_eligible_diagnosis(
        db=db,
        diagnosis=diagnosis,
    )

    revealed_levels = tuple(
        db.execute(
            select(HintEvent.level)
            .where(
                HintEvent.diagnosis_id == diagnosis.id,
                HintEvent.student_alias_id == student_alias_id,
            )
            .order_by(HintEvent.level.asc())
        )
        .scalars()
        .all()
    )

    next_level = _calculate_next_hint_level(
        revealed_levels=revealed_levels,
    )

    return HintProgressResult(
        diagnosis_id=diagnosis.id,
        attempt_id=attempt.id,
        student_alias_id=student_alias_id,
        misconception_id=misconception_id,
        revealed_levels=revealed_levels,
        next_level=next_level,
        maximum_level=MAX_HINT_LEVEL,
        completed=next_level is None,
    )


def reveal_next_hint(
    *,
    db: Session,
    diagnosis_id: UUID,
    student_alias_id: UUID,
) -> HintDeliveryResult:
    """
    Reveal and persist the next approved hint for a diagnosis.

    Progressive delivery rules:

        first request  -> level 1
        second request -> level 2
        third request  -> level 3

    The service refuses to:

    - reveal hints for another student's attempt;
    - reveal hints for an ineligible diagnosis;
    - reveal inactive hints;
    - skip levels;
    - reveal more than three levels;
    - reveal the same level twice.
    """

    diagnosis, attempt = _get_owned_diagnosis_context(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    misconception_id = _require_hint_eligible_diagnosis(
        db=db,
        diagnosis=diagnosis,
    )

    revealed_levels = tuple(
        db.execute(
            select(HintEvent.level)
            .where(
                HintEvent.diagnosis_id == diagnosis.id,
                HintEvent.student_alias_id == student_alias_id,
            )
            .order_by(HintEvent.level.asc())
        )
        .scalars()
        .all()
    )

    next_level = _calculate_next_hint_level(
        revealed_levels=revealed_levels,
    )

    if next_level is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "All approved hint levels have already been revealed "
                "for this diagnosis."
            ),
        )

    hint_template = _get_active_hint_template(
        db=db,
        misconception_id=misconception_id,
        level=next_level,
    )

    hint_event = HintEvent(
        student_alias_id=student_alias_id,
        attempt_id=attempt.id,
        diagnosis_id=diagnosis.id,
        hint_template_id=hint_template.id,
        level=next_level,
    )

    db.add(hint_event)

    try:
        db.commit()
        db.refresh(hint_event)
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This hint level has already been revealed for "
                "the diagnosis."
            ),
        ) from exc
    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to record the hint event.",
        ) from exc

    return HintDeliveryResult(
        hint_event_id=hint_event.id,
        diagnosis_id=diagnosis.id,
        attempt_id=attempt.id,
        student_alias_id=student_alias_id,
        hint_template_id=hint_template.id,
        misconception_id=misconception_id,
        level=hint_event.level,
        hint_text=hint_template.hint_text,
        is_final_level=hint_event.level == MAX_HINT_LEVEL,
        remaining_levels=max(
            0,
            MAX_HINT_LEVEL - hint_event.level,
        ),
        created_at=hint_event.created_at,
    )


def list_revealed_hints(
    *,
    db: Session,
    diagnosis_id: UUID,
    student_alias_id: UUID,
) -> list[HintDeliveryResult]:
    """
    Return all hints already revealed for one diagnosis.

    This operation does not create new hint events.
    """

    diagnosis, attempt = _get_owned_diagnosis_context(
        db=db,
        diagnosis_id=diagnosis_id,
        student_alias_id=student_alias_id,
    )

    misconception_id = _require_hint_eligible_diagnosis(
        db=db,
        diagnosis=diagnosis,
    )

    rows = db.execute(
        select(
            HintEvent,
            HintTemplate,
        )
        .join(
            HintTemplate,
            HintTemplate.id == HintEvent.hint_template_id,
        )
        .where(
            HintEvent.diagnosis_id == diagnosis.id,
            HintEvent.student_alias_id == student_alias_id,
        )
        .order_by(HintEvent.level.asc())
    ).all()

    results: list[HintDeliveryResult] = []

    for hint_event, hint_template in rows:
        results.append(
            HintDeliveryResult(
                hint_event_id=hint_event.id,
                diagnosis_id=diagnosis.id,
                attempt_id=attempt.id,
                student_alias_id=student_alias_id,
                hint_template_id=hint_template.id,
                misconception_id=misconception_id,
                level=hint_event.level,
                hint_text=hint_template.hint_text,
                is_final_level=(
                    hint_event.level == MAX_HINT_LEVEL
                ),
                remaining_levels=max(
                    0,
                    MAX_HINT_LEVEL - hint_event.level,
                ),
                created_at=hint_event.created_at,
            )
        )

    return results


def get_hint_usage_count(
    *,
    db: Session,
    diagnosis_id: UUID,
) -> int:
    """
    Return the number of hint levels already revealed for a diagnosis.
    """

    count = db.execute(
        select(
            func.count(HintEvent.id)
        ).where(
            HintEvent.diagnosis_id == diagnosis_id,
        )
    ).scalar_one()

    return int(count)


def _get_owned_diagnosis_context(
    *,
    db: Session,
    diagnosis_id: UUID,
    student_alias_id: UUID,
) -> tuple[Diagnosis, Attempt]:
    """
    Load a diagnosis and verify that its attempt belongs to the student.
    """

    row = db.execute(
        select(
            Diagnosis,
            Attempt,
        )
        .join(
            Attempt,
            Attempt.id == Diagnosis.attempt_id,
        )
        .where(
            Diagnosis.id == diagnosis_id,
        )
    ).one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis was not found.",
        )

    diagnosis, attempt = row

    if attempt.student_alias_id != student_alias_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The diagnosis does not belong to the supplied "
                "student alias."
            ),
        )

    return diagnosis, attempt


def _normalize_diagnosis_value(value: object) -> str:
    """
    Normalize persisted strings and enum-like values for reliable comparison.

    Older diagnoses may contain enum objects, mixed-case strings, or stale
    ``no_action`` values created before Sprint 9 persisted ``next_action``.
    """

    if value is None:
        return ""

    raw_value = getattr(value, "value", value)

    return str(raw_value).strip().lower()


def _require_hint_eligible_diagnosis(
    *,
    db: Session,
    diagnosis: Diagnosis,
) -> UUID:
    """
    Validate that the diagnosis is eligible for progressive hints.

    A confident diagnosis with a primary misconception is intrinsically
    eligible for progressive hints. If an older persisted row still contains
    ``no_action`` even though the diagnosis contract resolves to
    ``show_hint``, repair that stale value in place.

    Any explicit non-hint action other than the legacy ``no_action`` fallback
    remains rejected.
    """

    normalized_state = _normalize_diagnosis_value(
        diagnosis.state
    )
    normalized_next_action = _normalize_diagnosis_value(
        diagnosis.next_action
    )

    if normalized_state != HINT_ELIGIBLE_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Hints are available only for confident "
                "misconception diagnoses."
            ),
        )

    if diagnosis.primary_misconception_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A hint cannot be selected because the diagnosis "
                "has no primary misconception."
            ),
        )

    if normalized_next_action == HINT_ELIGIBLE_NEXT_ACTION:
        return diagnosis.primary_misconception_id

    if normalized_next_action in {"", "no_action"}:
        diagnosis.next_action = HINT_ELIGIBLE_NEXT_ACTION
        diagnosis.updated_at = datetime.utcnow()

        try:
            db.add(diagnosis)
            db.commit()
            db.refresh(diagnosis)
        except Exception as exc:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "The diagnosis is hint-eligible, but its persisted "
                    "intervention state could not be repaired."
                ),
            ) from exc

        return diagnosis.primary_misconception_id

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "This diagnosis currently recommends "
            f"'{normalized_next_action}' instead of a hint intervention."
        ),
    )


def _get_active_hint_template(
    *,
    db: Session,
    misconception_id: UUID,
    level: int,
) -> HintTemplate:
    """
    Load the active approved hint template for a misconception and level.
    """

    hint_template = db.execute(
        select(HintTemplate).where(
            HintTemplate.misconception_id == misconception_id,
            HintTemplate.level == level,
            HintTemplate.active.is_(True),
        )
    ).scalar_one_or_none()

    if hint_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No active level-{level} hint is configured "
                "for this misconception."
            ),
        )

    return hint_template


def _calculate_next_hint_level(
    *,
    revealed_levels: tuple[int, ...],
) -> int | None:
    """
    Calculate the next sequential hint level.

    Invalid stored sequences are rejected instead of silently skipping levels.
    """

    if not revealed_levels:
        return 1

    normalized_levels = tuple(
        sorted(
            set(revealed_levels)
        )
    )

    expected_prefix = tuple(
        range(
            1,
            len(normalized_levels) + 1,
        )
    )

    if normalized_levels != expected_prefix:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Stored hint history is not sequential. "
                "Hint delivery cannot continue safely."
            ),
        )

    highest_level = normalized_levels[-1]

    if highest_level >= MAX_HINT_LEVEL:
        return None

    return highest_level + 1


__all__ = [
    "HintDeliveryResult",
    "HintProgressResult",
    "MAX_HINT_LEVEL",
    "get_hint_progress",
    "get_hint_usage_count",
    "list_revealed_hints",
    "reveal_next_hint",
]