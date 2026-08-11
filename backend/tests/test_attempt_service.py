from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.attempt import AttemptCreate
from app.services import attempt_service


class FakeQuery:
    """
    Minimal SQLAlchemy query double used by attempt_service.py.

    The service only calls:
    db.query(Model).filter(...).first()
    """

    def __init__(self, result: object | None) -> None:
        self._result = result

    def filter(self, *args: object, **kwargs: object) -> "FakeQuery":
        return self

    def first(self) -> object | None:
        return self._result


class FakeDatabase:
    """
    Lightweight Session double for Sprint 10 attempt-service tests.
    """

    def __init__(
        self,
        *,
        student_alias: object | None = None,
        problem: object | None = None,
        fail_flush: bool = False,
        fail_commit: bool = False,
    ) -> None:
        self.student_alias = student_alias
        self.problem = problem
        self.fail_flush = fail_flush
        self.fail_commit = fail_commit

        self.added: list[object] = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.refresh_count = 0

    def query(self, model: object) -> FakeQuery:
        model_name = getattr(model, "__name__", "")

        if model_name == "StudentAlias":
            return FakeQuery(self.student_alias)

        if model_name == "Problem":
            return FakeQuery(self.problem)

        return FakeQuery(None)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        self.flush_count += 1

        if self.fail_flush:
            raise SQLAlchemyError(
                "Simulated database flush failure."
            )

    def commit(self) -> None:
        self.commit_count += 1

        if self.fail_commit:
            raise SQLAlchemyError(
                "Simulated database commit failure."
            )

    def rollback(self) -> None:
        self.rollback_count += 1

    def refresh(self, instance: object) -> None:
        self.refresh_count += 1


def make_student_alias(
    *,
    consent_status: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        consent_status=consent_status,
    )


def make_problem(
    *,
    active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        active=active,
    )


def make_valid_payload(
    *,
    student_alias_id=None,
    problem_id=None,
    **overrides: object,
) -> AttemptCreate:
    data: dict[str, object] = {
        "student_alias_id": student_alias_id or uuid4(),
        "problem_id": problem_id or uuid4(),
        "final_answer": "The answer is 42.",
        "written_reasoning": "I used a valid approach to solve the problem.",
        "source_code": "print(42)",
        "speech_transcript": None,
        "selected_language": "python",
        "response_time_seconds": 30,
        "normalized_reasoning": None,
        "speech_audio_reference": None,
        "speech_audio_retained": False,
        "speech_processing_status": "not_provided",
        "input_modality": "text_code",
        "input_language": "english",
        "detected_language": None,
    }

    data.update(overrides)

    return AttemptCreate(**data)


def make_valid_db(
    *,
    consent_status: bool = True,
    active_problem: bool = True,
) -> tuple[FakeDatabase, SimpleNamespace, SimpleNamespace]:
    student_alias = make_student_alias(
        consent_status=consent_status,
    )
    problem = make_problem(
        active=active_problem,
    )

    db = FakeDatabase(
        student_alias=student_alias,
        problem=problem,
    )

    return db, student_alias, problem


def test_create_attempt_persists_standard_text_code_submission() -> None:
    db, student_alias, problem = make_valid_db()

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
    )

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert len(db.added) == 1
    assert db.added[0] is attempt
    assert db.flush_count == 1
    assert db.commit_count == 1
    assert db.refresh_count == 1
    assert db.rollback_count == 0

    assert attempt.student_alias_id == student_alias.id
    assert attempt.problem_id == problem.id
    assert attempt.final_answer == "The answer is 42."
    assert attempt.written_reasoning == (
        "I used a valid approach to solve the problem."
    )
    assert attempt.source_code == "print(42)"
    assert attempt.selected_language == "python"
    assert attempt.input_modality == "text_code"
    assert attempt.input_language == "english"
    assert attempt.speech_processing_status == "not_provided"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("EN", "english"),
        ("eng", "english"),
        ("TE", "telugu"),
        ("tel", "telugu"),
        ("HI", "hindi"),
        ("hin", "hindi"),
        ("English", "english"),
        ("Telugu", "telugu"),
    ],
)
def test_input_language_is_normalized(
    raw_value: str,
    expected: str,
) -> None:
    db, student_alias, problem = make_valid_db()

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
        input_language=raw_value,
    )

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert attempt.input_language == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("text", "text"),
        ("code", "code"),
        ("speech", "speech"),
        ("text+code", "text_code"),
        ("text+speech", "text_speech"),
        ("code+speech", "code_speech"),
        ("text+code+speech", "text_code_speech"),
        ("text-code", "text_code"),
    ],
)
def test_input_modality_is_normalized(
    raw_value: str,
    expected: str,
) -> None:
    db, student_alias, problem = make_valid_db()

    kwargs: dict[str, object] = {
        "student_alias_id": student_alias.id,
        "problem_id": problem.id,
        "input_modality": raw_value,
    }

    if "speech" in expected:
        kwargs.update(
            {
                "speech_transcript": "Spoken reasoning.",
                "speech_processing_status": "completed",
            }
        )

    payload = make_valid_payload(**kwargs)

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert attempt.input_modality == expected


def test_normalized_reasoning_is_persisted() -> None:
    db, student_alias, problem = make_valid_db()

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
        normalized_reasoning=(
            "Binary search requires sorted input."
        ),
    )

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert attempt.normalized_reasoning == (
        "Binary search requires sorted input."
    )


def test_speech_submission_persists_multimodal_metadata() -> None:
    db, student_alias, problem = make_valid_db()

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
        speech_transcript=(
            "Each recursive call must move closer to the base case."
        ),
        speech_audio_reference="audio://attempt/example-001",
        speech_audio_retained=True,
        speech_processing_status="completed",
        input_modality="text_code_speech",
        input_language="TE",
        detected_language="tel",
    )

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert attempt.speech_transcript == (
        "Each recursive call must move closer to the base case."
    )
    assert attempt.speech_audio_reference == (
        "audio://attempt/example-001"
    )
    assert attempt.speech_audio_retained is True
    assert attempt.speech_processing_status == "completed"
    assert attempt.input_modality == "text_code_speech"
    assert attempt.input_language == "telugu"
    assert attempt.detected_language == "telugu"


def test_retained_audio_without_reference_is_rejected_by_schema() -> None:
    with pytest.raises(
        ValueError,
        match="speech_audio_reference is required",
    ):
        make_valid_payload(
            speech_audio_retained=True,
            speech_audio_reference=None,
            speech_transcript="Spoken explanation.",
            input_modality="text_speech",
            speech_processing_status="completed",
        )


def test_speech_metadata_without_speech_modality_is_rejected_by_schema() -> None:
    with pytest.raises(
        ValueError,
        match="input_modality must include speech",
    ):
        make_valid_payload(
            speech_transcript="Spoken explanation.",
            input_modality="text_code",
            speech_processing_status="completed",
        )


def test_active_speech_processing_without_speech_input_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="requires speech input",
    ):
        make_valid_payload(
            speech_transcript=None,
            speech_audio_reference=None,
            input_modality="text",
            speech_processing_status="processing",
        )


def test_invalid_input_modality_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input modality",
    ):
        make_valid_payload(
            input_modality="video",
        )


def test_invalid_speech_processing_status_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid speech processing status",
    ):
        make_valid_payload(
            speech_processing_status="finished",
        )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("PY", "python"),
        ("python3", "python"),
        ("python 3", "python"),
        ("C Language", "c"),
        ("text / no code", "text"),
        ("no code", "text"),
    ],
)
def test_programming_language_is_normalized(
    raw_value: str,
    expected: str,
) -> None:
    db, student_alias, problem = make_valid_db()

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
        selected_language=raw_value,
    )

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert attempt.selected_language == expected


def test_optional_text_is_trimmed_before_persistence() -> None:
    db, student_alias, problem = make_valid_db()

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
        final_answer="   answer   ",
        source_code="   print('x')   ",
        normalized_reasoning="   normalized reasoning   ",
    )

    attempt = attempt_service.create_attempt(
        db=db,
        payload=payload,
    )

    assert attempt.final_answer == "answer"
    assert attempt.source_code == "print('x')"
    assert attempt.normalized_reasoning == "normalized reasoning"


def test_missing_student_alias_returns_404() -> None:
    problem = make_problem()

    db = FakeDatabase(
        student_alias=None,
        problem=problem,
    )

    payload = make_valid_payload(
        problem_id=problem.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.create_attempt(
            db=db,
            payload=payload,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Student alias session not found."
    assert db.commit_count == 0


def test_student_without_consent_is_rejected() -> None:
    db, student_alias, problem = make_valid_db(
        consent_status=False,
    )

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.create_attempt(
            db=db,
            payload=payload,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Student consent is required before submitting an attempt."
    )
    assert db.commit_count == 0


def test_missing_problem_returns_404() -> None:
    student_alias = make_student_alias()

    db = FakeDatabase(
        student_alias=student_alias,
        problem=None,
    )

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.create_attempt(
            db=db,
            payload=payload,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Problem not found."
    assert db.commit_count == 0


def test_inactive_problem_is_rejected() -> None:
    db, student_alias, problem = make_valid_db(
        active_problem=False,
    )

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.create_attempt(
            db=db,
            payload=payload,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Cannot submit an attempt for an inactive problem."
    )
    assert db.commit_count == 0


def test_database_flush_failure_rolls_back() -> None:
    student_alias = make_student_alias()
    problem = make_problem()

    db = FakeDatabase(
        student_alias=student_alias,
        problem=problem,
        fail_flush=True,
    )

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.create_attempt(
            db=db,
            payload=payload,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Unable to save the student attempt."
    assert db.flush_count == 1
    assert db.commit_count == 0
    assert db.rollback_count == 1


def test_database_commit_failure_rolls_back() -> None:
    student_alias = make_student_alias()
    problem = make_problem()

    db = FakeDatabase(
        student_alias=student_alias,
        problem=problem,
        fail_commit=True,
    )

    payload = make_valid_payload(
        student_alias_id=student_alias.id,
        problem_id=problem.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.create_attempt(
            db=db,
            payload=payload,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Unable to save the student attempt."
    assert db.flush_count == 1
    assert db.commit_count == 1
    assert db.rollback_count == 1


def test_get_attempt_by_id_returns_saved_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = SimpleNamespace(
        id=uuid4(),
    )

    class LookupDatabase:
        def query(self, model: object) -> FakeQuery:
            return FakeQuery(attempt)

    result = attempt_service.get_attempt_by_id(
        db=LookupDatabase(),
        attempt_id=attempt.id,
    )

    assert result is attempt


def test_get_attempt_by_id_returns_404_when_missing() -> None:
    class LookupDatabase:
        def query(self, model: object) -> FakeQuery:
            return FakeQuery(None)

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        attempt_service.get_attempt_by_id(
            db=LookupDatabase(),
            attempt_id=uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Attempt not found."