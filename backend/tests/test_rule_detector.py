from __future__ import annotations

from dataclasses import replace

import pytest

from app.schemas.diagnosis import (
    DiagnosisNextAction,
    DiagnosisState,
    EvidenceSource,
    EvidenceStrength,
    RuleEvidence,
)
from app.services.evidence_extractor import EvidenceSignals
from app.services.rule_detector import (
    SUPPORTED_RULE_CODES,
    detect_misconception,
)


def make_evidence(
    text: str,
    *,
    source: EvidenceSource = EvidenceSource.RULE_ENGINE,
    strength: EvidenceStrength = EvidenceStrength.STRONG,
) -> RuleEvidence:
    return RuleEvidence(
        source=source,
        strength=strength,
        text=text,
        metadata={},
    )


def make_signals(
    *,
    evidence: list[RuleEvidence] | None = None,
    weak_submission: bool = False,
) -> EvidenceSignals:
    """
    Create neutral EvidenceSignals.

    Individual tests use dataclasses.replace() to enable only the exact
    signal required by the rule under test.
    """

    return EvidenceSignals(
        evidence=evidence or [],
        problem_array=None,
        problem_array_is_unsorted=False,
        reasoning_mentions_binary_search=False,
        code_uses_binary_search=False,
        code_uses_linear_search=False,
        recursive_call_detected=False,
        recursive_function_name=None,
        base_case_detected=False,
        missing_base_case=False,
        recursive_call_same_argument=False,
        recursive_call_increasing_argument=False,
        recursive_call_decreasing_argument=False,
        recursive_call_unknown_progress=False,
        weak_submission=weak_submission,

        # Sprint 8: M4
        parameter_reassignment_claims_caller_mutation=False,
        pass_by_value_confusion_detected=False,
        swap_uses_only_local_reassignment=False,
        pointer_based_swap_detected=False,
        return_based_swap_detected=False,

        # Sprint 8: M5
        stack_heap_confusion_detected=False,
        single_stack_frame_claim_detected=False,
        locals_survive_return_claim_detected=False,
        recursive_locals_on_heap_claim_detected=False,
    )


def test_supported_rules_include_all_five_misconceptions() -> None:
    assert SUPPORTED_RULE_CODES == frozenset(
        {
            "M1",
            "M2",
            "M3",
            "M4",
            "M5",
        }
    )


def test_m4_confident_when_local_reassignment_is_claimed_to_change_caller() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Changing the local parameters changes the caller variables.",
                source=EvidenceSource.WRITTEN_REASONING,
            ),
            make_evidence(
                "Swap function only reassigns local parameters.",
                source=EvidenceSource.SOURCE_CODE,
            ),
        ],
    )

    signals = replace(
        signals,
        parameter_reassignment_claims_caller_mutation=True,
        swap_uses_only_local_reassignment=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M4"},
    )

    assert result.state == DiagnosisState.CONFIDENT
    assert result.misconception_code == "M4"
    assert result.confidence >= 0.75
    assert result.next_action == DiagnosisNextAction.SHOW_HINT
    assert result.evidence


def test_m4_confident_for_explicit_pass_by_value_confusion() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Pass by value changes the original variable.",
                source=EvidenceSource.WRITTEN_REASONING,
            )
        ],
    )

    signals = replace(
        signals,
        pass_by_value_confusion_detected=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M4"},
    )

    assert result.state == DiagnosisState.CONFIDENT
    assert result.misconception_code == "M4"
    assert result.next_action == DiagnosisNextAction.SHOW_HINT


def test_m4_possible_for_local_swap_without_explanation() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Swap function only reassigns local parameters.",
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.MEDIUM,
            )
        ],
    )

    signals = replace(
        signals,
        swap_uses_only_local_reassignment=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M4"},
    )

    assert result.state == DiagnosisState.POSSIBLE
    assert result.misconception_code == "M4"
    assert 0.45 <= result.confidence < 0.75
    assert (
        result.next_action
        == DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION
    )


@pytest.mark.parametrize(
    "correct_evidence_text",
    [
        "Uses pointers to modify caller variables.",
        "Passes addresses and dereferences the pointers.",
        "Returns the swapped values to the caller.",
        "Correctly explains pass-by-value.",
    ],
)
def test_m4_correct_structure_returns_no_misconception(
    correct_evidence_text: str,
) -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                correct_evidence_text,
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
            )
        ],
    )

    signals = replace(
        signals,
        pointer_based_swap_detected=(
            "pointer" in correct_evidence_text.lower()
            or "addresses" in correct_evidence_text.lower()
        ),
        return_based_swap_detected=(
            "returns" in correct_evidence_text.lower()
        ),
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M4"},
    )

    assert result.state == DiagnosisState.NO_MISCONCEPTION
    assert result.misconception_code is None
    assert result.confidence >= 0.75
    assert result.next_action == DiagnosisNextAction.NO_ACTION


@pytest.mark.parametrize(
    (
        "signal_name",
        "evidence_text",
    ),
    [
        (
            "stack_heap_confusion_detected",
            "Stack and heap are the same.",
        ),
        (
            "single_stack_frame_claim_detected",
            "Recursive calls reuse one stack frame.",
        ),
        (
            "locals_survive_return_claim_detected",
            "Local variables remain after the function returns.",
        ),
        (
            "recursive_locals_on_heap_claim_detected",
            "All recursive local variables are stored on the heap.",
        ),
    ],
)
def test_m5_direct_confusion_returns_confident(
    signal_name: str,
    evidence_text: str,
) -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                evidence_text,
                source=EvidenceSource.WRITTEN_REASONING,
            )
        ],
    )

    signals = replace(
        signals,
        **{
            signal_name: True,
        },
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M5"},
    )

    assert result.state == DiagnosisState.CONFIDENT
    assert result.misconception_code == "M5"
    assert result.confidence >= 0.75
    assert result.next_action == DiagnosisNextAction.SHOW_HINT
    assert result.evidence


def test_m5_partial_memory_explanation_returns_possible() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Recursive call memory model is incomplete.",
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.MEDIUM,
            )
        ],
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M5"},
    )

    assert result.state == DiagnosisState.POSSIBLE
    assert result.misconception_code == "M5"
    assert 0.45 <= result.confidence < 0.75
    assert (
        result.next_action
        == DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION
    )


@pytest.mark.parametrize(
    "correct_evidence_text",
    [
        "Each recursive call has its own stack frame.",
        "One frame per active call.",
        "Stack frame is removed when the call returns.",
        "Correctly distinguishes stack and heap.",
    ],
)
def test_m5_correct_memory_model_returns_no_misconception(
    correct_evidence_text: str,
) -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                correct_evidence_text,
                source=EvidenceSource.WRITTEN_REASONING,
            )
        ],
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M5"},
    )

    assert result.state == DiagnosisState.NO_MISCONCEPTION
    assert result.misconception_code is None
    assert result.confidence >= 0.75
    assert result.next_action == DiagnosisNextAction.NO_ACTION


def test_m4_signal_is_blocked_when_only_m5_is_allowed() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Pass by value changes the original variable.",
                source=EvidenceSource.WRITTEN_REASONING,
            )
        ],
    )

    signals = replace(
        signals,
        pass_by_value_confusion_detected=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M5"},
    )

    assert result.state == DiagnosisState.INSUFFICIENT
    assert result.misconception_code is None
    assert result.confidence < 0.45


def test_m5_signal_is_blocked_when_only_m4_is_allowed() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Only one stack frame is used.",
                source=EvidenceSource.WRITTEN_REASONING,
            )
        ],
    )

    signals = replace(
        signals,
        single_stack_frame_claim_detected=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M4"},
    )

    assert result.state == DiagnosisState.INSUFFICIENT
    assert result.misconception_code is None
    assert result.confidence < 0.45


def test_unknown_rule_codes_return_insufficient() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Some observable evidence.",
                strength=EvidenceStrength.MEDIUM,
            )
        ],
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M99"},
    )

    assert result.state == DiagnosisState.INSUFFICIENT
    assert result.misconception_code is None
    assert result.confidence == 0.0
    assert result.next_action == DiagnosisNextAction.ASK_CLARIFICATION


def test_weak_submission_without_strong_evidence_returns_insufficient() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Submission contains limited evidence for reliable diagnosis.",
                strength=EvidenceStrength.WEAK,
            )
        ],
        weak_submission=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M4", "M5"},
    )

    assert result.state == DiagnosisState.INSUFFICIENT
    assert result.misconception_code is None
    assert result.confidence < 0.45
    assert result.next_action == DiagnosisNextAction.ASK_CLARIFICATION


def test_m3_remains_more_specific_than_m2() -> None:
    """
    Regression test: same-argument recursion must be diagnosed as M3 even
    when the missing-base-case M2 signal is also present.
    """

    signals = make_signals(
        evidence=[
            make_evidence(
                "Recursive self-call detected inside function 'solve'.",
                source=EvidenceSource.SOURCE_CODE,
            ),
            make_evidence(
                "Recursive call appears to reuse the same argument.",
                source=EvidenceSource.SOURCE_CODE,
            ),
            make_evidence(
                "No clear base-case condition was detected.",
                source=EvidenceSource.SOURCE_CODE,
            ),
        ],
    )

    signals = replace(
        signals,
        recursive_call_detected=True,
        recursive_function_name="solve",
        base_case_detected=False,
        missing_base_case=True,
        recursive_call_same_argument=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M2", "M3"},
    )

    assert result.state == DiagnosisState.CONFIDENT
    assert result.misconception_code == "M3"
    assert "M2" in result.alternative_misconception_codes


def test_m3_alternative_is_removed_when_m2_is_not_allowed() -> None:
    signals = make_signals(
        evidence=[
            make_evidence(
                "Recursive self-call detected inside function 'solve'.",
                source=EvidenceSource.SOURCE_CODE,
            ),
            make_evidence(
                "Recursive call appears to reuse the same argument.",
                source=EvidenceSource.SOURCE_CODE,
            ),
        ],
    )

    signals = replace(
        signals,
        recursive_call_detected=True,
        recursive_function_name="solve",
        missing_base_case=True,
        recursive_call_same_argument=True,
    )

    result = detect_misconception(
        signals,
        allowed_rule_codes={"M3"},
    )

    assert result.state == DiagnosisState.CONFIDENT
    assert result.misconception_code == "M3"
    assert result.alternative_misconception_codes == []