from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.schemas.diagnosis import (
    DiagnosisNextAction,
    DiagnosisResponse,
    DiagnosisState,
    EvidenceSource,
    EvidenceStrength,
    RuleDetectionResult,
    RuleEvidence,
)
from app.services import diagnosis_service


class FakeDatabase:
    """
    Lightweight database double.

    The diagnosis service uses raw SQL through db.execute(), followed by
    commit() or rollback(). These tests capture those operations without
    requiring a real PostgreSQL database.
    """

    def __init__(
        self,
        *,
        fail_commit: bool = False,
    ) -> None:
        self.executed: list[tuple[str, dict | None]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self.fail_commit = fail_commit

    def execute(
        self,
        statement: object,
        parameters: dict | None = None,
    ) -> SimpleNamespace:
        self.executed.append(
            (
                str(statement),
                parameters,
            )
        )

        return SimpleNamespace()

    def commit(self) -> None:
        self.commit_count += 1

        if self.fail_commit:
            raise RuntimeError(
                "Simulated database commit failure."
            )

    def rollback(self) -> None:
        self.rollback_count += 1


def make_attempt(
    *,
    problem_id: UUID | None = None,
    **overrides: object,
) -> SimpleNamespace:
    data: dict[str, object] = {
        "id": uuid4(),
        "student_alias_id": uuid4(),
        "problem_id": problem_id or uuid4(),
        "parent_attempt_id": None,
        "retry_number": 0,
        "final_answer": "Sample answer",
        "written_reasoning": "Sample reasoning",
        "normalized_reasoning": None,
        "source_code": "print('sample')",
        "speech_transcript": None,
        "speech_audio_reference": None,
        "speech_audio_retained": False,
        "speech_processing_status": "not_provided",
        "input_modality": "text_code",
        "input_language": "english",
        "detected_language": None,
        "selected_language": "python",
        "response_time_seconds": 30,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    data.update(overrides)

    return SimpleNamespace(**data)


def make_problem(
    code: str,
    *,
    misconception_codes: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        code=code,
        title=f"Problem {code}",
        topic="Test topic",
        statement="Test problem statement",
        difficulty="easy",
        expected_language="python",
        rule_context={
            "misconception_codes": (
                misconception_codes
                if misconception_codes is not None
                else []
            ),
        },
        created_at=datetime.utcnow(),
    )


def make_misconception(
    code: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        code=code,
        name=f"Misconception {code}",
        topic="Test topic",
    )


def make_evidence(
    text: str,
) -> RuleEvidence:
    return RuleEvidence(
        source=EvidenceSource.WRITTEN_REASONING,
        strength=EvidenceStrength.STRONG,
        text=text,
        metadata={},
    )


def make_rule_result(
    *,
    state: DiagnosisState,
    misconception_code: str | None,
    confidence: float,
    next_action: DiagnosisNextAction,
    evidence: list[RuleEvidence] | None = None,
    alternatives: list[str] | None = None,
) -> RuleDetectionResult:
    return RuleDetectionResult(
        state=state,
        misconception_code=misconception_code,
        confidence=confidence,
        evidence=evidence or [],
        alternative_misconception_codes=alternatives or [],
        decision_reason="Test rule decision.",
        next_action=next_action,
    )


@pytest.fixture
def fixed_created_at() -> datetime:
    return datetime(
        2026,
        8,
        5,
        18,
        30,
        0,
    )


def configure_new_diagnosis_flow(
    monkeypatch: pytest.MonkeyPatch,
    *,
    attempt: SimpleNamespace,
    problem: SimpleNamespace,
    rule_result: RuleDetectionResult,
    fixed_created_at: datetime,
) -> None:
    """
    Configure the service so create_diagnosis_from_attempt() executes the
    new-diagnosis branch without touching a real database.
    """

    monkeypatch.setattr(
        diagnosis_service,
        "_get_attempt_or_404",
        lambda db, attempt_id: attempt,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_existing_diagnosis_for_attempt",
        lambda db, attempt_id, model_version: None,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_problem_or_404",
        lambda db, problem_id: problem,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "extract_evidence",
        lambda *, attempt, problem: SimpleNamespace(),
    )

    monkeypatch.setattr(
        diagnosis_service,
        "detect_misconception",
        lambda signals, allowed_rule_codes: rule_result,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_diagnosis_created_at",
        lambda db, diagnosis_id: fixed_created_at,
    )


def test_model_version_is_rule_v1_9() -> None:
    assert diagnosis_service.MODEL_VERSION == "rule-v1.9"


@pytest.mark.parametrize(
    (
        "problem_code",
        "expected_codes",
    ),
    [
        ("P1", {"M1"}),
        ("P2", {"M2", "M3"}),
        ("P3", {"M2", "M3"}),
        ("P4", {"M4"}),
        ("P5", {"M5"}),
    ],
)
def test_seeded_problem_allowlist(
    problem_code: str,
    expected_codes: set[str],
) -> None:
    problem = make_problem(
        problem_code,
    )

    assert (
        diagnosis_service._get_allowed_misconception_codes(
            problem
        )
        == expected_codes
    )


def test_unknown_problem_uses_rule_context_allowlist() -> None:
    problem = make_problem(
        "PX",
        misconception_codes=[
            "m4",
            " M5 ",
        ],
    )

    result = (
        diagnosis_service._get_allowed_misconception_codes(
            problem
        )
    )

    assert result == {
        "M4",
        "M5",
    }


def test_unknown_problem_without_configuration_has_empty_allowlist() -> None:
    problem = make_problem(
        "PX",
        misconception_codes=[],
    )

    assert (
        diagnosis_service._get_allowed_misconception_codes(
            problem
        )
        == set()
    )


@pytest.mark.parametrize(
    (
        "state",
        "misconception_code",
        "confidence",
        "evidence",
    ),
    [
        (
            DiagnosisState.CONFIDENT,
            "M4",
            0.92,
            [make_evidence("Strong M4 evidence.")],
        ),
        (
            DiagnosisState.POSSIBLE,
            "M5",
            0.62,
            [make_evidence("Possible M5 evidence.")],
        ),
        (
            DiagnosisState.NO_MISCONCEPTION,
            None,
            0.95,
            [make_evidence("Correct solution evidence.")],
        ),
        (
            DiagnosisState.INSUFFICIENT,
            None,
            0.0,
            [],
        ),
    ],
)
def test_valid_final_diagnosis_contracts(
    state: DiagnosisState,
    misconception_code: str | None,
    confidence: float,
    evidence: list[RuleEvidence],
) -> None:
    diagnosis_service._validate_final_diagnosis_contract(
        state=state,
        misconception_code=misconception_code,
        confidence=confidence,
        evidence=evidence,
    )


@pytest.mark.parametrize(
    (
        "state",
        "misconception_code",
        "confidence",
        "evidence",
        "expected_message",
    ),
    [
        (
            DiagnosisState.CONFIDENT,
            None,
            0.90,
            [make_evidence("Evidence exists.")],
            "requires a misconception code",
        ),
        (
            DiagnosisState.POSSIBLE,
            None,
            0.60,
            [make_evidence("Evidence exists.")],
            "requires a misconception code",
        ),
        (
            DiagnosisState.NO_MISCONCEPTION,
            "M4",
            0.95,
            [make_evidence("Evidence exists.")],
            "must not carry a misconception code",
        ),
        (
            DiagnosisState.INSUFFICIENT,
            "M5",
            0.0,
            [],
            "must not carry a misconception code",
        ),
        (
            DiagnosisState.CONFIDENT,
            "M4",
            0.92,
            [],
            "requires at least one observable evidence item",
        ),
    ],
)
def test_invalid_final_diagnosis_contracts_raise_http_500(
    state: DiagnosisState,
    misconception_code: str | None,
    confidence: float,
    evidence: list[RuleEvidence],
    expected_message: str,
) -> None:
    with pytest.raises(
        HTTPException,
    ) as exc_info:
        diagnosis_service._validate_final_diagnosis_contract(
            state=state,
            misconception_code=misconception_code,
            confidence=confidence,
            evidence=evidence,
        )

    assert exc_info.value.status_code == 500
    assert expected_message in str(
        exc_info.value.detail
    )


@pytest.mark.parametrize(
    "confidence",
    [
        -0.01,
        1.01,
    ],
)
def test_invalid_confidence_is_rejected(
    confidence: float,
) -> None:
    with pytest.raises(
        HTTPException,
    ) as exc_info:
        diagnosis_service._validate_final_diagnosis_contract(
            state=DiagnosisState.INSUFFICIENT,
            misconception_code=None,
            confidence=confidence,
            evidence=[],
        )

    assert exc_info.value.status_code == 500
    assert (
        "between 0 and 1"
        in str(exc_info.value.detail)
    )


def test_create_m4_diagnosis_persists_rule_v1_9(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()
    problem = make_problem("P4")
    attempt = make_attempt(
        problem_id=problem.id,
    )
    misconception = make_misconception("M4")

    rule_result = make_rule_result(
        state=DiagnosisState.CONFIDENT,
        misconception_code="M4",
        confidence=0.92,
        next_action=DiagnosisNextAction.SHOW_HINT,
        evidence=[
            make_evidence(
                "Changing local parameters does not automatically "
                "change caller variables."
            )
        ],
    )

    configure_new_diagnosis_flow(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        rule_result=rule_result,
        fixed_created_at=fixed_created_at,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_misconception_by_code_or_404",
        lambda db, code: misconception,
    )

    response = (
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )
    )

    assert isinstance(
        response,
        DiagnosisResponse,
    )
    assert response.state == DiagnosisState.CONFIDENT
    assert response.confidence == 0.92
    assert response.model_version == "rule-v1.9"
    assert response.next_action == DiagnosisNextAction.SHOW_HINT
    assert response.primary_misconception is not None
    assert response.primary_misconception.code == "M4"
    assert len(response.evidence) == 1
    assert db.commit_count == 1
    assert db.rollback_count == 0

    diagnosis_insert = next(
        parameters
        for statement, parameters in db.executed
        if "INSERT INTO diagnoses" in statement
    )

    assert diagnosis_insert is not None
    assert diagnosis_insert["state"] == "confident"
    assert diagnosis_insert["model_version"] == "rule-v1.9"
    assert (
        diagnosis_insert["primary_misconception_id"]
        == misconception.id
    )


def test_create_m5_diagnosis_persists_correct_primary_label(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()
    problem = make_problem("P5")
    attempt = make_attempt(
        problem_id=problem.id,
    )
    misconception = make_misconception("M5")

    rule_result = make_rule_result(
        state=DiagnosisState.CONFIDENT,
        misconception_code="M5",
        confidence=0.91,
        next_action=DiagnosisNextAction.SHOW_HINT,
        evidence=[
            make_evidence(
                "Recursive calls reuse one stack frame."
            )
        ],
    )

    configure_new_diagnosis_flow(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        rule_result=rule_result,
        fixed_created_at=fixed_created_at,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_misconception_by_code_or_404",
        lambda db, code: misconception,
    )

    response = (
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )
    )

    assert response.state == DiagnosisState.CONFIDENT
    assert response.primary_misconception is not None
    assert response.primary_misconception.code == "M5"
    assert response.confidence == 0.91
    assert response.model_version == "rule-v1.9"
    assert db.commit_count == 1


def test_no_misconception_preserves_evidence_without_primary_label(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()
    problem = make_problem("P5")
    attempt = make_attempt(
        problem_id=problem.id,
    )

    rule_result = make_rule_result(
        state=DiagnosisState.NO_MISCONCEPTION,
        misconception_code=None,
        confidence=0.95,
        next_action=DiagnosisNextAction.NO_ACTION,
        evidence=[
            make_evidence(
                "Each recursive call has its own stack frame."
            )
        ],
    )

    configure_new_diagnosis_flow(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        rule_result=rule_result,
        fixed_created_at=fixed_created_at,
    )

    response = (
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )
    )

    assert (
        response.state
        == DiagnosisState.NO_MISCONCEPTION
    )
    assert response.primary_misconception is None
    assert response.confidence == 0.95
    assert response.next_action == DiagnosisNextAction.NO_ACTION
    assert len(response.evidence) == 1
    assert db.commit_count == 1

    diagnosis_insert = next(
        parameters
        for statement, parameters in db.executed
        if "INSERT INTO diagnoses" in statement
    )

    assert diagnosis_insert is not None
    assert (
        diagnosis_insert["primary_misconception_id"]
        is None
    )


def test_insufficient_result_is_persisted_without_primary_label(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()
    problem = make_problem("P4")
    attempt = make_attempt(
        problem_id=problem.id,
    )

    rule_result = make_rule_result(
        state=DiagnosisState.INSUFFICIENT,
        misconception_code=None,
        confidence=0.0,
        next_action=DiagnosisNextAction.ASK_CLARIFICATION,
        evidence=[],
    )

    configure_new_diagnosis_flow(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        rule_result=rule_result,
        fixed_created_at=fixed_created_at,
    )

    response = (
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )
    )

    assert response.state == DiagnosisState.INSUFFICIENT
    assert response.primary_misconception is None
    assert response.confidence == 0.0
    assert (
        response.next_action
        == DiagnosisNextAction.ASK_CLARIFICATION
    )
    assert db.commit_count == 1


def test_cross_topic_detection_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    """
    P4 allows only M4. A detector output of M5 must be converted into an
    insufficient result instead of being persisted as a cross-topic label.
    """

    db = FakeDatabase()
    problem = make_problem("P4")
    attempt = make_attempt(
        problem_id=problem.id,
    )

    rule_result = make_rule_result(
        state=DiagnosisState.CONFIDENT,
        misconception_code="M5",
        confidence=0.91,
        next_action=DiagnosisNextAction.SHOW_HINT,
        evidence=[
            make_evidence(
                "Stack and heap are the same."
            )
        ],
    )

    configure_new_diagnosis_flow(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        rule_result=rule_result,
        fixed_created_at=fixed_created_at,
    )

    response = (
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )
    )

    assert response.state == DiagnosisState.INSUFFICIENT
    assert response.primary_misconception is None
    assert response.confidence == 0.0
    assert (
        response.next_action
        == DiagnosisNextAction.ASK_CLARIFICATION
    )
    assert response.decision_reason is not None
    assert "cross-topic result was rejected" in (
        response.decision_reason
    )


def test_existing_rule_v1_9_diagnosis_is_returned_without_new_insert(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()
    attempt = make_attempt()
    diagnosis_id = uuid4()

    existing = SimpleNamespace(
        id=diagnosis_id,
    )

    expected_response = DiagnosisResponse(
        id=diagnosis_id,
        attempt_id=attempt.id,
        state=DiagnosisState.INSUFFICIENT,
        confidence=0.0,
        primary_misconception=None,
        evidence=[],
        alternatives=[],
        model_version="rule-v1.9",
        decision_reason=(
            "Existing diagnosis returned."
        ),
        next_action=DiagnosisNextAction.ASK_CLARIFICATION,
        created_at=fixed_created_at,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_attempt_or_404",
        lambda db, attempt_id: attempt,
    )

    captured_model_versions: list[str] = []

    def fake_get_existing(
        db: object,
        attempt_id: UUID,
        model_version: str,
    ) -> SimpleNamespace:
        captured_model_versions.append(
            model_version
        )
        return existing

    monkeypatch.setattr(
        diagnosis_service,
        "_get_existing_diagnosis_for_attempt",
        fake_get_existing,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_build_existing_diagnosis_response",
        lambda db, diagnosis_id: expected_response,
    )

    response = (
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )
    )

    assert response is expected_response
    assert captured_model_versions == [
        "rule-v1.9"
    ]
    assert db.executed == []
    assert db.commit_count == 0


def test_commit_failure_rolls_back_and_returns_http_500(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase(
        fail_commit=True,
    )
    problem = make_problem("P4")
    attempt = make_attempt(
        problem_id=problem.id,
    )
    misconception = make_misconception("M4")

    rule_result = make_rule_result(
        state=DiagnosisState.CONFIDENT,
        misconception_code="M4",
        confidence=0.92,
        next_action=DiagnosisNextAction.SHOW_HINT,
        evidence=[
            make_evidence(
                "Explicit M4 evidence."
            )
        ],
    )

    configure_new_diagnosis_flow(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        rule_result=rule_result,
        fixed_created_at=fixed_created_at,
    )

    monkeypatch.setattr(
        diagnosis_service,
        "_get_misconception_by_code_or_404",
        lambda db, code: misconception,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        diagnosis_service.create_diagnosis_from_attempt(
            db=db,
            attempt_id=attempt.id,
        )

    assert exc_info.value.status_code == 500
    assert (
        exc_info.value.detail
        == "Unable to persist diagnosis result."
    )
    assert db.commit_count == 1
    assert db.rollback_count == 1


@pytest.mark.parametrize(
    (
        "state",
        "confidence",
        "has_primary",
        "expected_action",
    ),
    [
        (
            "confident",
            0.92,
            True,
            DiagnosisNextAction.SHOW_HINT,
        ),
        (
            "possible",
            0.62,
            True,
            DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
        ),
        (
            "insufficient",
            0.0,
            False,
            DiagnosisNextAction.ASK_CLARIFICATION,
        ),
        (
            "no_misconception",
            0.95,
            False,
            DiagnosisNextAction.NO_ACTION,
        ),
    ],
)
def test_existing_diagnosis_next_action_mapping(
    state: str,
    confidence: float,
    has_primary: bool,
    expected_action: DiagnosisNextAction,
) -> None:
    result = (
        diagnosis_service._next_action_for_existing_diagnosis(
            state=state,
            confidence=confidence,
            has_primary_misconception=has_primary,
        )
    )

    assert result == expected_action


# ---------------------------------------------------------------------------
# Sprint 10 normalized-reasoning / multimodal diagnosis integration
# ---------------------------------------------------------------------------


def _configure_real_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    attempt: SimpleNamespace,
    problem: SimpleNamespace,
    fixed_created_at: datetime,
) -> None:
    """
    Keep the real Sprint 10 extractor + rule detector, while replacing only
    persistence lookup boundaries that would otherwise require PostgreSQL.
    """

    monkeypatch.setattr(
        diagnosis_service,
        "_get_attempt_or_404",
        lambda db, attempt_id: attempt,
    )
    monkeypatch.setattr(
        diagnosis_service,
        "_get_existing_diagnosis_for_attempt",
        lambda db, attempt_id, model_version: None,
    )
    monkeypatch.setattr(
        diagnosis_service,
        "_get_problem_or_404",
        lambda db, problem_id: problem,
    )
    monkeypatch.setattr(
        diagnosis_service,
        "_get_diagnosis_created_at",
        lambda db, diagnosis_id: fixed_created_at,
    )


def test_normalized_reasoning_flows_through_real_diagnosis_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    """
    Raw reasoning contains a misconception-like statement, but Sprint 10
    normalized reasoning corrects it. The diagnosis must use the normalized
    representation rather than stale raw wording.
    """

    db = FakeDatabase()

    problem = make_problem(
        "P1",
        misconception_codes=["M1"],
    )
    problem.statement = (
        "Search for a target in the unsorted array [7, 2, 9, 1]."
    )
    problem.rule_context = {
        "misconception_codes": ["M1"],
        "array": [7, 2, 9, 1],
    }

    attempt = make_attempt(
        problem_id=problem.id,
        final_answer="Use linear search.",
        written_reasoning=(
            "Binary search works directly on the unsorted array."
        ),
        normalized_reasoning=(
            "Binary search should not be used directly on unsorted data. "
            "Use linear search instead."
        ),
        source_code="""
int search(int a[], int n, int target) {
    for (int i = 0; i < n; i++) {
        if (a[i] == target) return i;
    }
    return -1;
}
""",
        speech_transcript=None,
        input_modality="text_code",
        input_language="telugu",
        detected_language="telugu",
        selected_language="c",
    )

    _configure_real_pipeline(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        fixed_created_at=fixed_created_at,
    )

    response = diagnosis_service.create_diagnosis_from_attempt(
        db=db,
        attempt_id=attempt.id,
    )

    assert response.model_version == "rule-v1.9"
    assert response.state == DiagnosisState.NO_MISCONCEPTION
    assert response.primary_misconception is None
    assert response.next_action == DiagnosisNextAction.NO_ACTION
    assert db.commit_count == 1


def test_speech_only_m5_misconception_flows_through_real_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()

    problem = make_problem(
        "P5",
        misconception_codes=["M5"],
    )
    problem.statement = (
        "Explain stack frames and heap allocation during recursion."
    )

    attempt = make_attempt(
        problem_id=problem.id,
        final_answer=None,
        written_reasoning="",
        normalized_reasoning=None,
        source_code="",
        speech_transcript=(
            "Recursive calls reuse one stack frame and local variables "
            "remain after the function returns."
        ),
        input_modality="speech",
        input_language="english",
        detected_language="english",
        speech_processing_status="completed",
    )

    misconception = make_misconception("M5")

    _configure_real_pipeline(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        fixed_created_at=fixed_created_at,
    )
    monkeypatch.setattr(
        diagnosis_service,
        "_get_misconception_by_code_or_404",
        lambda db, code: misconception,
    )

    response = diagnosis_service.create_diagnosis_from_attempt(
        db=db,
        attempt_id=attempt.id,
    )

    assert response.model_version == "rule-v1.9"
    assert response.state == DiagnosisState.CONFIDENT
    assert response.primary_misconception is not None
    assert response.primary_misconception.code == "M5"
    assert response.next_action == DiagnosisNextAction.SHOW_HINT
    assert any(
        item.source == EvidenceSource.SPEECH_TRANSCRIPT
        for item in response.evidence
    )
    assert db.commit_count == 1


def test_correct_speech_only_m5_explanation_returns_no_misconception(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()

    problem = make_problem(
        "P5",
        misconception_codes=["M5"],
    )
    problem.statement = (
        "Explain stack frames and heap allocation during recursion."
    )

    attempt = make_attempt(
        problem_id=problem.id,
        final_answer=None,
        written_reasoning="",
        normalized_reasoning=None,
        source_code="",
        speech_transcript=(
            "Each recursive call has its own stack frame. "
            "The stack frame is removed when the call returns, and "
            "ordinary local variables are not stored on the heap."
        ),
        input_modality="speech",
        input_language="english",
        detected_language="english",
        speech_processing_status="completed",
    )

    _configure_real_pipeline(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        fixed_created_at=fixed_created_at,
    )

    response = diagnosis_service.create_diagnosis_from_attempt(
        db=db,
        attempt_id=attempt.id,
    )

    assert response.model_version == "rule-v1.9"
    assert response.state == DiagnosisState.NO_MISCONCEPTION
    assert response.primary_misconception is None
    assert response.next_action == DiagnosisNextAction.NO_ACTION
    assert any(
        item.source == EvidenceSource.SPEECH_TRANSCRIPT
        for item in response.evidence
    )
    assert db.commit_count == 1


def test_mixed_text_code_speech_recursion_pipeline_preserves_speech_evidence(
    monkeypatch: pytest.MonkeyPatch,
    fixed_created_at: datetime,
) -> None:
    db = FakeDatabase()

    problem = make_problem(
        "P3",
        misconception_codes=["M2", "M3"],
    )
    problem.statement = "Compute the recursive sum of N numbers."

    attempt = make_attempt(
        problem_id=problem.id,
        final_answer="The recursive call should use n - 1.",
        written_reasoning=(
            "The call must move toward the stopping condition."
        ),
        normalized_reasoning=(
            "The recursive argument must decrease toward the base case."
        ),
        source_code="""
int sum(int n) {
    if (n <= 0) return 0;
    return n + sum(n - 1);
}
""",
        speech_transcript=(
            "Each call uses a smaller argument until the base case."
        ),
        input_modality="text_code_speech",
        input_language="telugu",
        detected_language="telugu",
        speech_processing_status="completed",
        selected_language="c",
    )

    _configure_real_pipeline(
        monkeypatch,
        attempt=attempt,
        problem=problem,
        fixed_created_at=fixed_created_at,
    )

    response = diagnosis_service.create_diagnosis_from_attempt(
        db=db,
        attempt_id=attempt.id,
    )

    assert response.model_version == "rule-v1.9"
    assert response.state == DiagnosisState.NO_MISCONCEPTION
    assert response.primary_misconception is None
    assert response.next_action == DiagnosisNextAction.NO_ACTION
    assert any(
        item.source == EvidenceSource.SOURCE_CODE
        for item in response.evidence
    )
    assert any(
        item.source == EvidenceSource.SPEECH_TRANSCRIPT
        for item in response.evidence
    )
    assert db.commit_count == 1
