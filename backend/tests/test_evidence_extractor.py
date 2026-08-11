from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.diagnosis import (
    EvidenceSource,
    EvidenceStrength,
)
from app.services.evidence_extractor import extract_evidence


def make_attempt(
    *,
    final_answer: str = "",
    written_reasoning: str = "",
    normalized_reasoning: str | None = None,
    source_code: str = "",
    speech_transcript: str = "",
    input_modality: str = "text",
    input_language: str = "english",
    detected_language: str | None = None,
) -> SimpleNamespace:
    """
    Create a lightweight attempt object matching the fields consumed by
    extract_evidence().
    """

    return SimpleNamespace(
        final_answer=final_answer,
        written_reasoning=written_reasoning,
        normalized_reasoning=normalized_reasoning,
        source_code=source_code,
        speech_transcript=speech_transcript,
        input_modality=input_modality,
        input_language=input_language,
        detected_language=detected_language,
    )


def make_problem(
    *,
    code: str,
    statement: str,
    rule_context: dict | None = None,
) -> SimpleNamespace:
    """
    Create a lightweight problem object matching the fields consumed by
    extract_evidence().
    """

    return SimpleNamespace(
        code=code,
        statement=statement,
        rule_context=rule_context or {},
    )


def evidence_texts(signals: object) -> list[str]:
    return [
        item.text.lower()
        for item in signals.evidence
    ]


def test_m4_detects_claim_that_local_reassignment_changes_caller() -> None:
    attempt = make_attempt(
        final_answer=(
            "Changing the local parameters changes the caller variables."
        ),
        written_reasoning=(
            "Local reassignment modifies the caller, so the original "
            "numbers are swapped."
        ),
        source_code="""
def swap(a, b):
    temp = a
    a = b
    b = temp
""",
    )

    problem = make_problem(
        code="P4",
        statement=(
            "Explain whether swapping two function parameters changes "
            "the caller's original variables."
        ),
        rule_context={
            "misconception_codes": ["M4"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert (
        signals.parameter_reassignment_claims_caller_mutation
        is True
    )

    assert signals.swap_uses_only_local_reassignment is True
    assert signals.pointer_based_swap_detected is False


def test_m4_detects_explicit_pass_by_value_confusion() -> None:
    attempt = make_attempt(
        final_answer=(
            "Pass by value changes the original variable."
        ),
        written_reasoning=(
            "Parameters are references by default, so assigning a new "
            "value changes the caller."
        ),
        source_code="""
def update(value):
    value = 100
""",
    )

    problem = make_problem(
        code="P4",
        statement=(
            "Explain whether assigning to a function parameter changes "
            "the caller's variable."
        ),
        rule_context={
            "misconception_codes": ["M4"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.pass_by_value_confusion_detected is True
    assert (
        signals.parameter_reassignment_claims_caller_mutation
        is False
    )


def test_m4_detects_pointer_based_swap() -> None:
    attempt = make_attempt(
        final_answer=(
            "The caller variables change because their addresses are passed."
        ),
        written_reasoning=(
            "The function dereferences the pointers and updates the "
            "original variables."
        ),
        source_code="""
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

int main(void) {
    int x = 10;
    int y = 20;
    swap(&x, &y);
    return 0;
}
""",
    )

    problem = make_problem(
        code="P4",
        statement=(
            "Swap two values and explain whether the caller-visible "
            "variables change."
        ),
        rule_context={
            "misconception_codes": ["M4"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.pointer_based_swap_detected is True
    assert signals.pass_by_value_confusion_detected is False
    assert (
        signals.parameter_reassignment_claims_caller_mutation
        is False
    )


def test_m4_detects_return_based_solution() -> None:
    attempt = make_attempt(
        final_answer=(
            "The function returns the swapped values and the caller "
            "assigns them."
        ),
        written_reasoning=(
            "Local parameters do not automatically rebind the caller's "
            "variables."
        ),
        source_code="""
def swap(a, b):
    return b, a

x, y = swap(x, y)
""",
    )

    problem = make_problem(
        code="P4",
        statement="Swap two values using a function.",
        rule_context={
            "misconception_codes": ["M4"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.return_based_swap_detected is True
    assert signals.pass_by_value_confusion_detected is False


def test_m5_detects_stack_and_heap_equivalence_claim() -> None:
    attempt = make_attempt(
        final_answer=(
            "Stack and heap are the same."
        ),
        written_reasoning=(
            "Function call frames are stored on the heap."
        ),
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain stack frames and heap allocation during recursion."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.stack_heap_confusion_detected is True


def test_m5_detects_single_stack_frame_claim() -> None:
    attempt = make_attempt(
        final_answer=(
            "Only one stack frame is used."
        ),
        written_reasoning=(
            "Recursive calls reuse one stack frame for every call."
        ),
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain what happens in memory during recursive calls."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.single_stack_frame_claim_detected is True


def test_m5_detects_local_variables_survive_return_claim() -> None:
    attempt = make_attempt(
        final_answer=(
            "Local variables remain after the function returns."
        ),
        written_reasoning=(
            "Stack variables survive after return and can still be used."
        ),
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain the lifetime of local variables in a stack frame."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.locals_survive_return_claim_detected is True


def test_m5_detects_recursive_locals_on_heap_claim() -> None:
    attempt = make_attempt(
        final_answer=(
            "All recursive local variables are stored on the heap."
        ),
        written_reasoning=(
            "Recursion does not create separate stack frames."
        ),
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain stack and heap behaviour during recursion."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.recursive_locals_on_heap_claim_detected is True


def test_correct_m5_explanation_does_not_trigger_confusion_flags() -> None:
    attempt = make_attempt(
        final_answer=(
            "Each recursive call has its own stack frame."
        ),
        written_reasoning=(
            "The frame contains that call's parameters and local variables. "
            "The frame is removed when the call returns. Heap objects have "
            "a separate lifetime."
        ),
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain memory behaviour during recursive calls."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.stack_heap_confusion_detected is False
    assert signals.single_stack_frame_claim_detected is False
    assert signals.locals_survive_return_claim_detected is False
    assert signals.recursive_locals_on_heap_claim_detected is False


def test_weak_submission_is_marked_as_weak() -> None:
    attempt = make_attempt(
        final_answer="idk",
        written_reasoning="",
        source_code="",
        speech_transcript="",
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain stack frames and heap allocation during recursion."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.weak_submission is True

    weak_evidence = [
        item
        for item in signals.evidence
        if item.source == EvidenceSource.RULE_ENGINE
        and item.strength == EvidenceStrength.WEAK
    ]

    assert weak_evidence
    assert any(
        "limited evidence" in item.text.lower()
        for item in weak_evidence
    )


@pytest.mark.parametrize(
    (
        "reasoning",
        "expected_attribute",
    ),
    [
        (
            "Stack and heap are the same.",
            "stack_heap_confusion_detected",
        ),
        (
            "Only one stack frame is used.",
            "single_stack_frame_claim_detected",
        ),
        (
            "Local variables remain after the function returns.",
            "locals_survive_return_claim_detected",
        ),
        (
            "All recursive local variables are stored on the heap.",
            "recursive_locals_on_heap_claim_detected",
        ),
    ],
)
def test_m5_individual_phrases_activate_expected_signal(
    reasoning: str,
    expected_attribute: str,
) -> None:
    attempt = make_attempt(
        final_answer=reasoning,
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain stack and heap behaviour during recursion."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert getattr(
        signals,
        expected_attribute,
    ) is True

# ---------------------------------------------------------------------------
# Sprint 10 multimodal / normalized-reasoning coverage
# ---------------------------------------------------------------------------


def test_normalized_reasoning_is_preferred_over_raw_written_reasoning() -> None:
    """
    When normalized reasoning exists, semantic misconception matching should use
    it rather than stale/conflicting raw written reasoning.
    """

    attempt = make_attempt(
        final_answer="",
        written_reasoning=(
            "Binary search works on any unsorted array."
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
        input_modality="text_code",
        input_language="telugu",
        detected_language="telugu",
    )

    problem = make_problem(
        code="P1",
        statement=(
            "Search for a target in an unsorted array."
        ),
        rule_context={
            "misconception_codes": ["M1"],
            "array": [7, 2, 9, 1],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.code_uses_linear_search is True
    assert signals.code_uses_binary_search is False
    assert (
        signals.reasoning_mentions_binary_search
        is False
    )

    texts = evidence_texts(signals)

    assert any(
        "binary search should not be used" in item
        for item in texts
    )


def test_written_reasoning_is_used_when_normalized_reasoning_is_missing() -> None:
    attempt = make_attempt(
        final_answer="",
        written_reasoning=(
            "Recursive calls reuse the same argument without reducing "
            "the problem size."
        ),
        normalized_reasoning=None,
        source_code="""
int sum(int n) {
    if (n <= 0) return 0;
    return n + sum(n);
}
""",
        input_modality="text_code",
    )

    problem = make_problem(
        code="P3",
        statement="Compute the recursive sum of N numbers.",
        rule_context={
            "misconception_codes": ["M2", "M3"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.recursive_call_detected is True
    assert signals.recursive_call_same_argument is True

    assert any(
        item.source == EvidenceSource.WRITTEN_REASONING
        for item in signals.evidence
    )


def test_speech_transcript_contributes_to_m5_misconception_evidence() -> None:
    attempt = make_attempt(
        final_answer="",
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
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain stack frames and heap allocation during recursion."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.single_stack_frame_claim_detected is True
    assert signals.locals_survive_return_claim_detected is True
    assert signals.weak_submission is False

    speech_items = [
        item
        for item in signals.evidence
        if item.source == EvidenceSource.SPEECH_TRANSCRIPT
    ]

    assert speech_items


def test_speech_only_correct_m5_explanation_does_not_trigger_confusion() -> None:
    attempt = make_attempt(
        final_answer="",
        written_reasoning="",
        normalized_reasoning=None,
        source_code="",
        speech_transcript=(
            "Each recursive call has its own stack frame. "
            "The stack frame is removed when the call returns, and "
            "ordinary local variables are not stored on the heap."
        ),
        input_modality="speech",
    )

    problem = make_problem(
        code="P5",
        statement="Explain memory behaviour during recursive calls.",
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.stack_heap_confusion_detected is False
    assert signals.single_stack_frame_claim_detected is False
    assert signals.locals_survive_return_claim_detected is False
    assert signals.recursive_locals_on_heap_claim_detected is False


def test_mixed_text_and_speech_evidence_is_preserved() -> None:
    attempt = make_attempt(
        final_answer=(
            "The recursive call should use n - 1."
        ),
        written_reasoning=(
            "The call has to move toward the stopping condition."
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
    )

    problem = make_problem(
        code="P3",
        statement="Compute the recursive sum of N numbers.",
        rule_context={
            "misconception_codes": ["M2", "M3"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.recursive_call_detected is True
    assert signals.base_case_detected is True
    assert signals.recursive_call_decreasing_argument is True
    assert signals.recursive_call_same_argument is False

    sources = {
        item.source
        for item in signals.evidence
    }

    assert EvidenceSource.SOURCE_CODE in sources
    assert EvidenceSource.SPEECH_TRANSCRIPT in sources


def test_source_code_detection_remains_unchanged_with_language_metadata() -> None:
    attempt = make_attempt(
        final_answer=(
            "The caller variables are updated through pointers."
        ),
        written_reasoning=(
            "C passes the addresses and dereferences the pointers."
        ),
        normalized_reasoning=(
            "Caller-visible mutation is performed through pointer "
            "dereferencing."
        ),
        source_code="""
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}
""",
        input_modality="text_code",
        input_language="telugu",
        detected_language="telugu",
    )

    problem = make_problem(
        code="P4",
        statement="Swap two values using a function.",
        rule_context={
            "misconception_codes": ["M4"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.pointer_based_swap_detected is True
    assert signals.swap_uses_only_local_reassignment is False
    assert signals.pass_by_value_confusion_detected is False


def test_normalized_reasoning_prevents_weak_submission_when_original_is_blank() -> None:
    attempt = make_attempt(
        final_answer="",
        written_reasoning="",
        normalized_reasoning=(
            "Each recursive call has its own stack frame and the frame "
            "is removed when the call returns."
        ),
        source_code="",
        speech_transcript="",
        input_modality="text",
        input_language="telugu",
        detected_language="telugu",
    )

    problem = make_problem(
        code="P5",
        statement=(
            "Explain stack frames and heap allocation during recursion."
        ),
        rule_context={
            "misconception_codes": ["M5"],
        },
    )

    signals = extract_evidence(
        attempt=attempt,
        problem=problem,
    )

    assert signals.weak_submission is False
