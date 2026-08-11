from __future__ import annotations

from collections.abc import Iterable

from app.schemas.diagnosis import (
    DiagnosisNextAction,
    DiagnosisState,
    EvidenceStrength,
    RuleDetectionResult,
    RuleEvidence,
)
from app.services.evidence_extractor import EvidenceSignals


SUPPORTED_RULE_CODES = frozenset(
    {
        "M1",
        "M2",
        "M3",
        "M4",
        "M5",
    }
)


def detect_misconception(
    signals: EvidenceSignals,
    allowed_rule_codes: Iterable[str] | None = None,
) -> RuleDetectionResult:
    """
    Detect a supported misconception from already-extracted evidence.

    Supported rules:
    - M1: Binary Search on Unsorted Data
    - M2: Missing or Incorrect Recursion Base Case
    - M3: Recursive Call Without Reducing Problem Size
    - M4: Pass-by-Value vs Pass-by-Reference Confusion
    - M5: Stack vs Heap Confusion

    Cross-topic protection:
    Only rules mapped to the selected problem are evaluated when
    ``allowed_rule_codes`` is supplied.

    Backward compatibility:
    When ``allowed_rule_codes`` is None, all currently supported rules are
    evaluated.

    Sprint 10:
    - The detector remains modality-agnostic and never reads raw attempt fields.
    - normalized_reasoning, speech transcripts, and language metadata are
      resolved by evidence_extractor.py before signals reach this layer.
    - Rule decisions therefore remain deterministic across text, code, speech,
      and mixed-modality attempts.
    - Weak/empty modality input must not create a misconception unless the
      extractor produced rule-specific observable evidence.

    This function never inspects raw source code or raw speech directly. It
    relies exclusively on EvidenceSignals produced by evidence_extractor.py.
    """

    allowed_rules = _normalize_allowed_rule_codes(allowed_rule_codes)

    if not allowed_rules:
        return _insufficient_result(
            evidence=_weak_or_general_evidence(signals),
            reason=(
                "No supported misconception rules are configured for this problem."
            ),
        )

    # A genuinely weak submission should not receive a confident diagnosis
    # unless the extractor still found a strong rule-specific signal.
    evidence_items = list(getattr(signals, "evidence", []) or [])

    has_strong_evidence = any(
        item.strength == EvidenceStrength.STRONG
        for item in evidence_items
    )

    if signals.weak_submission and not has_strong_evidence:
        return _insufficient_result(
            evidence=_weak_or_general_evidence(signals),
            reason=(
                "The submission does not contain enough observable reasoning or "
                "implementation evidence for a reliable diagnosis."
            ),
        )

    correct_result = _detect_supported_correct_structure(
        signals=signals,
        allowed_rules=allowed_rules,
    )
    if correct_result is not None:
        return correct_result

    # M3 is checked before M2 because no-progress recursion is more specific
    # than a general missing-base-case diagnosis.
    if "M3" in allowed_rules:
        result = _detect_m3_recursive_no_progress(signals)
        if result is not None:
            return _filter_alternatives(result, allowed_rules)

    if "M2" in allowed_rules:
        result = _detect_m2_missing_base_case(signals)
        if result is not None:
            return _filter_alternatives(result, allowed_rules)

    if "M1" in allowed_rules:
        result = _detect_m1_binary_search_unsorted(signals)
        if result is not None:
            return _filter_alternatives(result, allowed_rules)

    if "M4" in allowed_rules:
        result = _detect_m4_parameter_passing_confusion(signals)
        if result is not None:
            return _filter_alternatives(result, allowed_rules)

    if "M5" in allowed_rules:
        result = _detect_m5_stack_heap_confusion(signals)
        if result is not None:
            return _filter_alternatives(result, allowed_rules)

    return _insufficient_result(
        evidence=_weak_or_general_evidence(signals),
        reason=(
            "None of the misconception rules configured for this problem had "
            "enough observable evidence for a reliable diagnosis."
        ),
    )


def _detect_supported_correct_structure(
    *,
    signals: EvidenceSignals,
    allowed_rules: set[str],
) -> RuleDetectionResult | None:
    """
    Return a positive no-misconception result when the observable evidence
    directly contradicts every misconception configured for the problem.

    For M1, a correct result requires both:
    - reasoning that rejects binary search on the unsorted input, and
    - source-code evidence of a sequential linear-search implementation.

    NO_MISCONCEPTION means the submitted evidence supports a correct approach.
    INSUFFICIENT means the system does not have enough evidence to decide.
    """

    if "M1" in allowed_rules:
        correct_binary_search_rejection = any(
            (
                "binary search should not be used" in item.text.lower()
                or "correctly rejects binary search" in item.text.lower()
                or "uses linear search" in item.text.lower()
                or "linear-search pattern" in item.text.lower()
            )
            for item in signals.evidence
        )

        if (
            signals.problem_array_is_unsorted
            and not signals.reasoning_mentions_binary_search
            and not signals.code_uses_binary_search
            and signals.code_uses_linear_search
            and correct_binary_search_rejection
        ):
            evidence = _evidence_matching(
                signals,
                [
                    "Problem input array detected",
                    "Problem input array is not sorted",
                    "binary search should not be used",
                    "correctly rejects binary search",
                    "uses linear search",
                    "linear-search pattern",
                    "scans the array sequentially",
                ],
            )

            return RuleDetectionResult(
                state=DiagnosisState.NO_MISCONCEPTION,
                misconception_code=None,
                confidence=0.95,
                evidence=evidence,
                alternative_misconception_codes=[],
                decision_reason=(
                    "The student correctly recognizes that binary search requires "
                    "sorted input and implements a sequential linear search for the "
                    "unsorted array. The evidence is language-independent and may "
                    "come from either Python or C/C++ source analysis."
                ),
                next_action=DiagnosisNextAction.NO_ACTION,
            )

    recursion_rules_active = bool({"M2", "M3"} & allowed_rules)

    if (
        recursion_rules_active
        and signals.recursive_call_detected
        and signals.base_case_detected
        and signals.recursive_call_decreasing_argument
        and not signals.missing_base_case
        and not signals.recursive_call_same_argument
        and not signals.recursive_call_increasing_argument
    ):
        evidence = _evidence_matching(
            signals,
            [
                "Recursive self-call detected inside function",
                "base-case condition is present",
                "reduce the argument",
                "reduces the argument",
                "moves toward termination",
            ],
        )

        return RuleDetectionResult(
            state=DiagnosisState.NO_MISCONCEPTION,
            misconception_code=None,
            confidence=0.95,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The recursive implementation includes a stopping condition and "
                "reduces the recursive argument toward termination. These signals "
                "are accepted from supported Python or C/C++ source analysis."
            ),
            next_action=DiagnosisNextAction.NO_ACTION,
        )

    if "M4" in allowed_rules:
        correct_parameter_semantics = any(
            (
                _signal_enabled(
                    signals,
                    "correct_parameter_semantics_understood",
                ),
                _has_evidence_fragment(
                    signals,
                    [
                        "caller variables remain unchanged",
                        "original caller variables do not change",
                        "uses pointers to modify caller variables",
                        "passes addresses",
                        "dereferences the pointers",
                        "returns the swapped values",
                        "correctly explains pass-by-value",
                        "correctly explains parameter passing",
                    ],
                ),
            )
        )

        if (
            correct_parameter_semantics
            and not _signal_enabled(
                signals,
                "parameter_reassignment_claims_caller_mutation",
            )
            and not _signal_enabled(
                signals,
                "pass_by_value_confusion_detected",
            )
            and not _signal_enabled(
                signals,
                "swap_uses_only_local_reassignment",
            )
        ):
            evidence = _evidence_matching(
                signals,
                [
                    "caller variables remain unchanged",
                    "original caller variables do not change",
                    "uses pointers to modify caller variables",
                    "passes addresses",
                    "dereferences the pointers",
                    "returns the swapped values",
                    "correctly explains pass-by-value",
                    "correctly explains parameter passing",
                    "local parameter changes do not change the caller variables automatically",
                ],
            )

            return RuleDetectionResult(
                state=DiagnosisState.NO_MISCONCEPTION,
                misconception_code=None,
                confidence=0.95,
                evidence=evidence,
                alternative_misconception_codes=[],
                decision_reason=(
                    "The student correctly distinguishes local parameter changes "
                    "from caller-visible mutation and uses or explains an appropriate "
                    "mechanism such as pointers or returned values."
                ),
                next_action=DiagnosisNextAction.NO_ACTION,
            )

    if "M5" in allowed_rules:
        correct_memory_model = _has_evidence_fragment(
            signals,
            [
                "each recursive call has its own stack frame",
                "each recursive call gets its own stack frame",
                "each call has its own stack frame",
                "each call gets its own stack frame",
                "separate stack frame",
                "separate stack frames",
                "one frame per active call",
                "one stack frame per active call",
                "local variables are stored in the stack frame",
                "local variables belong to that call's stack frame",
                "local variables belong to each call's stack frame",
                "local variables exist while that call is active",
                "local variables are destroyed when the call returns",
                "local variables disappear when the call returns",
                "stack frame is removed when the call returns",
                "stack frame disappears when the call returns",
                "stack frame is destroyed when the call returns",
                "heap allocation has a separate lifetime",
                "heap memory has a separate lifetime",
                "heap memory follows different lifetime rules",
                "heap-allocated memory follows different lifetime rules",
                "correctly distinguishes stack and heap",
            ],
        )

        if (
            correct_memory_model
            and not _signal_enabled(
                signals,
                "stack_heap_confusion_detected",
            )
            and not _signal_enabled(
                signals,
                "single_stack_frame_claim_detected",
            )
            and not _signal_enabled(
                signals,
                "locals_survive_return_claim_detected",
            )
        ):
            evidence = _evidence_matching(
                signals,
                [
                    "each recursive call has its own stack frame",
                    "separate stack frame",
                    "local variables are stored in the stack frame",
                    "stack frame is removed when the call returns",
                    "heap allocation has a separate lifetime",
                    "correctly distinguishes stack and heap",
                    "one frame per active call",
                ],
            )

            return RuleDetectionResult(
                state=DiagnosisState.NO_MISCONCEPTION,
                misconception_code=None,
                confidence=0.95,
                evidence=evidence,
                alternative_misconception_codes=[],
                decision_reason=(
                    "The student correctly explains that active function calls use "
                    "separate stack frames and distinguishes stack-frame lifetime "
                    "from heap-allocation lifetime."
                ),
                next_action=DiagnosisNextAction.NO_ACTION,
            )

    return None


def _normalize_allowed_rule_codes(
    allowed_rule_codes: Iterable[str] | None,
) -> set[str]:
    """
    Normalize rule codes supplied by the diagnosis service.

    Unsupported rule codes are ignored.
    """

    if allowed_rule_codes is None:
        return set(SUPPORTED_RULE_CODES)

    normalized = {
        str(code).strip().upper()
        for code in allowed_rule_codes
        if code is not None and str(code).strip()
    }

    return normalized.intersection(SUPPORTED_RULE_CODES)


def _detect_m1_binary_search_unsorted(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M1:
    The student applies or endorses binary search for an unsorted array.

    The updated evidence extractor already distinguishes between:
    - using binary search incorrectly, and
    - correctly explaining that binary search must not be used.

    Therefore a correct rejection of binary search does not activate M1.
    """

    if not signals.problem_array_is_unsorted:
        return None

    has_reasoning_signal = signals.reasoning_mentions_binary_search
    has_code_signal = signals.code_uses_binary_search

    if not has_reasoning_signal and not has_code_signal:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "Problem input array is not sorted.",
            "Student reasoning proposes or endorses binary search",
            "Student code uses a binary-search pattern",
        ],
    )

    if has_reasoning_signal and has_code_signal:
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M1",
            confidence=0.92,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The problem input is unsorted, while both the student's reasoning "
                "and implementation use binary-search logic."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    return RuleDetectionResult(
        state=DiagnosisState.POSSIBLE,
        misconception_code="M1",
        confidence=0.68,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=(
            "The problem input is unsorted and one binary-search misuse signal was "
            "detected, but the second confirming signal is absent."
        ),
        next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
    )


def _detect_m2_missing_base_case(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M2:
    A recursive self-call exists inside the function, but no clear stopping
    condition is detected.
    """

    if not signals.recursive_call_detected:
        return None

    if signals.base_case_detected:
        return None

    if not signals.missing_base_case:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "Recursive self-call detected inside function",
            "no clear base-case condition was detected",
        ],
    )

    return RuleDetectionResult(
        state=DiagnosisState.CONFIDENT,
        misconception_code="M2",
        confidence=0.88,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=(
            "A recursive self-call is present, but the implementation does not "
            "contain a detectable stopping condition for the recursive process."
        ),
        next_action=DiagnosisNextAction.SHOW_HINT,
    )


def _detect_m3_recursive_no_progress(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M3:
    A recursive self-call exists, but its argument does not move toward
    termination.

    A verified decreasing argument suppresses the uncertain-progress branch.
    """

    if not signals.recursive_call_detected:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "Recursive self-call detected inside function",
            "reuse the same argument",
            "increase the argument",
            "argument progress is unclear",
            "no clear base-case condition was detected",
        ],
    )

    alternatives: list[str] = []

    if signals.missing_base_case:
        alternatives.append("M2")

    if signals.recursive_call_same_argument:
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M3",
            confidence=0.94,
            evidence=evidence,
            alternative_misconception_codes=alternatives,
            decision_reason=(
                "The recursive call reuses the same argument, so the problem size "
                "does not decrease between calls."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    if signals.recursive_call_increasing_argument:
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M3",
            confidence=0.94,
            evidence=evidence,
            alternative_misconception_codes=alternatives,
            decision_reason=(
                "The recursive call increases the argument instead of moving it "
                "toward a terminating condition."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    if signals.recursive_call_decreasing_argument:
        return None

    if signals.recursive_call_unknown_progress:
        return RuleDetectionResult(
            state=DiagnosisState.POSSIBLE,
            misconception_code="M3",
            confidence=0.58,
            evidence=evidence,
            alternative_misconception_codes=alternatives,
            decision_reason=(
                "A recursive self-call exists, but the extractor cannot verify that "
                "the recursive argument reduces the problem size."
            ),
            next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
        )

    return None



def _detect_m4_parameter_passing_confusion(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M4:
    The student assumes that reassigning local parameters automatically changes
    the caller's original variables, or otherwise confuses value, pointer, and
    reference semantics.

    This detector supports both explicit extractor flags and evidence-text
    matching. The optional flags allow evidence_extractor.py to become more
    structured without breaking this file in the meantime.
    """

    direct_confusion = any(
        (
            _signal_enabled(
                signals,
                "parameter_reassignment_claims_caller_mutation",
            ),
            _signal_enabled(
                signals,
                "pass_by_value_confusion_detected",
            ),
        )
    )

    local_swap_only = _signal_enabled(
        signals,
        "swap_uses_only_local_reassignment",
    )

    reasoning_confusion = _has_evidence_fragment(
        signals,
        [
            "changing the local parameters changes the caller variables",
            "reassigning parameters swaps the original variables",
            "caller variables are automatically changed",
            "local reassignment modifies the caller",
            "pass by value changes the original variable",
            "swap succeeds using only local assignments",
            "parameters are references by default",
        ],
    )

    code_only_local_swap = (
        local_swap_only
        or _has_evidence_fragment(
            signals,
            [
                "swap function only reassigns local parameters",
                "local parameter swap detected without pointers",
                "no pointer dereference was detected",
                "caller-visible mutation mechanism was not detected",
                "only local assignments were detected",
            ],
        )
    )

    correct_mechanism = any(
        (
            _signal_enabled(signals, "pointer_based_swap_detected"),
            _signal_enabled(signals, "return_based_swap_detected"),
            _signal_enabled(
                signals,
                "correct_parameter_semantics_understood",
            ),
            _has_evidence_fragment(
                signals,
                [
                    "uses pointers to modify caller variables",
                    "passes addresses",
                    "dereferences the pointers",
                    "returns the swapped values",
                    "caller variables remain unchanged without pointers",
                    "correctly explains pass-by-value",
                    "local parameter changes do not change the caller variables automatically",
                ],
            ),
        )
    )

    # Fully corrected M4 evidence: the student now understands caller-visible
    # mutation and the implementation is not merely a local-parameter swap.
    if (
        correct_mechanism
        and not direct_confusion
        and not reasoning_confusion
        and not code_only_local_swap
    ):
        return None

    # Partial correction: reasoning is now correct but the submitted swap still
    # only changes local parameters. Keep M4 as POSSIBLE so the retry can be
    # classified as Improving rather than Repeated.
    if (
        correct_mechanism
        and code_only_local_swap
        and not direct_confusion
        and not reasoning_confusion
    ):
        evidence = _evidence_matching(
            signals,
            [
                "local parameter changes do not change the caller variables automatically",
                "swap function only reassigns local parameters",
                "caller-visible mutation mechanism was not detected",
                "only local assignments were detected",
            ],
        )

        return RuleDetectionResult(
            state=DiagnosisState.POSSIBLE,
            misconception_code="M4",
            confidence=0.64,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The retry shows improved understanding of pass-by-value, but "
                "the implementation still changes only local parameters and does "
                "not yet demonstrate caller-visible mutation."
            ),
            next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
        )

    if not direct_confusion and not reasoning_confusion and not code_only_local_swap:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "changing the local parameters changes the caller variables",
            "reassigning parameters swaps the original variables",
            "caller variables are automatically changed",
            "local reassignment modifies the caller",
            "pass by value changes the original variable",
            "swap succeeds using only local assignments",
            "parameters are references by default",
            "swap function only reassigns local parameters",
            "local parameter swap detected without pointers",
            "no pointer dereference was detected",
            "caller-visible mutation mechanism was not detected",
            "only local assignments were detected",
        ],
    )

    if direct_confusion or (
        reasoning_confusion
        and code_only_local_swap
    ):
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M4",
            confidence=0.92,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The submission treats local parameter reassignment as if it "
                "automatically mutates the caller's original variables, without "
                "using or explaining the required pointer, reference, or return "
                "mechanism."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    return RuleDetectionResult(
        state=DiagnosisState.POSSIBLE,
        misconception_code="M4",
        confidence=0.66,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=(
            "The submission contains one observable parameter-passing confusion "
            "signal, but the available evidence is not strong enough to confirm "
            "whether the student understands caller-visible mutation."
        ),
        next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
    )


def _detect_m5_stack_heap_confusion(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M5:
    The student confuses stack frames, heap allocation, local-variable lifetime,
    or recursive-call memory behaviour.
    """

    # Keep the individual M5 signals separate. The broad
    # stack_heap_confusion_detected flag is useful as a candidate signal,
    # but it must not by itself force a CONFIDENT diagnosis. Otherwise a
    # partially corrected retry is scored exactly like the original strong
    # misconception and the evolution layer can only report "Repeated".
    single_frame_confusion = _signal_enabled(
        signals,
        "single_stack_frame_claim_detected",
    )
    locals_survive_return_confusion = _signal_enabled(
        signals,
        "locals_survive_return_claim_detected",
    )
    recursive_locals_on_heap_confusion = _signal_enabled(
        signals,
        "recursive_locals_on_heap_claim_detected",
    )
    broad_stack_heap_confusion = _signal_enabled(
        signals,
        "stack_heap_confusion_detected",
    )

    explicit_confusion = any(
        (
            single_frame_confusion,
            locals_survive_return_confusion,
            recursive_locals_on_heap_confusion,
        )
    )

    strong_confusion = _has_evidence_fragment(
        signals,
        [
            "all recursive local variables are stored on the heap",
            "recursive calls reuse one stack frame",
            "only one stack frame is used",
            "local variables remain after the function returns",
            "stack variables survive after return",
            "stack and heap are the same",
            "function call frames are stored on the heap",
            "each recursive call overwrites the same local variables",
        ],
    )

    partial_confusion = _has_evidence_fragment(
        signals,
        [
            "memory explanation confuses stack and heap",
            "stack-frame lifetime is unclear",
            "heap lifetime is unclear",
            "recursive call memory model is incomplete",
            "does not distinguish active call frames",
            "local variable lifetime is incorrectly explained",
        ],
    )

    correct_memory_model = _has_evidence_fragment(
        signals,
        [
            "each recursive call has its own stack frame",
            "each recursive call gets its own stack frame",
            "each call has its own stack frame",
            "each call gets its own stack frame",
            "separate stack frame",
            "separate stack frames",
            "one frame per active call",
            "one stack frame per active call",
            "local variables are stored in the stack frame",
            "local variables belong to that call's stack frame",
            "local variables belong to each call's stack frame",
            "local variables exist while that call is active",
            "local variables are destroyed when the call returns",
            "local variables disappear when the call returns",
            "stack frame is removed when the call returns",
            "stack frame disappears when the call returns",
            "stack frame is destroyed when the call returns",
            "heap allocation has a separate lifetime",
            "heap memory has a separate lifetime",
            "heap memory follows different lifetime rules",
            "heap-allocated memory follows different lifetime rules",
            "correctly distinguishes stack and heap",
        ],
    )

    if (
        correct_memory_model
        and not explicit_confusion
        and not strong_confusion
        and not partial_confusion
        and not broad_stack_heap_confusion
    ):
        return None

    if (
        not explicit_confusion
        and not strong_confusion
        and not partial_confusion
        and not broad_stack_heap_confusion
    ):
        return None

    evidence = _evidence_matching(
        signals,
        [
            "all recursive local variables are stored on the heap",
            "recursive calls reuse one stack frame",
            "only one stack frame is used",
            "local variables remain after the function returns",
            "stack variables survive after return",
            "stack and heap are the same",
            "function call frames are stored on the heap",
            "each recursive call overwrites the same local variables",
            "memory explanation confuses stack and heap",
            "stack-frame lifetime is unclear",
            "heap lifetime is unclear",
            "recursive call memory model is incomplete",
            "does not distinguish active call frames",
            "local variable lifetime is incorrectly explained",
        ],
    )

    # Sprint 9 Improving transition:
    # A retry can contain a verified correction (for example, the student now
    # states that each active recursive call has its own stack frame) while still
    # expressing residual uncertainty about local-variable or heap lifetime.
    # That mixed state is weaker than the original direct misconception and must
    # therefore become POSSIBLE, not CONFIDENT. Otherwise the evolution layer can
    # only classify the retry as Repeated instead of Improving.
    if (
        correct_memory_model
        and explicit_confusion
        and not strong_confusion
    ):
        return RuleDetectionResult(
            state=DiagnosisState.POSSIBLE,
            misconception_code="M5",
            confidence=0.64,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The retry shows a meaningful correction in the student's memory "
                "model, but some stack/heap or local-variable-lifetime uncertainty "
                "remains. The misconception is therefore still plausible, but no "
                "longer strong enough for a confident M5 diagnosis."
            ),
            next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
        )

    if explicit_confusion or strong_confusion:
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M5",
            confidence=0.91,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The student's explanation contains a direct stack/heap or "
                "stack-frame-lifetime misconception, such as reusing one frame "
                "for all recursive calls, placing ordinary recursive locals on "
                "the heap, or retaining local variables after return."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    # Broad or mixed M5 evidence is intentionally POSSIBLE rather than
    # CONFIDENT. This allows a strong parent diagnosis to become a weaker
    # retry diagnosis and therefore be classified as Improving.
    return RuleDetectionResult(
        state=DiagnosisState.POSSIBLE,
        misconception_code="M5",
        confidence=0.62,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=(
            "The submission still contains a stack/heap or lifetime concern, but "
            "the available evidence is partial, ambiguous, or mixed with correct "
            "memory-model reasoning. More evidence is required before confirming M5."
        ),
        next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
    )


def _signal_enabled(
    signals: EvidenceSignals,
    attribute_name: str,
) -> bool:
    """
    Read an optional boolean EvidenceSignals attribute safely.

    Structured extractor flags may evolve independently of this detector.
    A safe accessor keeps rule evaluation backward-compatible when a signal is
    absent from an older EvidenceSignals object.
    """

    return bool(
        getattr(
            signals,
            attribute_name,
            False,
        )
    )


def _evidence_items(
    signals: EvidenceSignals,
) -> list[RuleEvidence]:
    """
    Return extracted evidence safely.

    Sprint 10 keeps modality and normalization handling in the extractor.
    The detector consumes only the resulting structured evidence contract.
    """

    return list(
        getattr(
            signals,
            "evidence",
            [],
        )
        or []
    )


def _has_evidence_fragment(
    signals: EvidenceSignals,
    text_fragments: list[str],
) -> bool:
    """
    Return True when any extracted evidence contains a relevant phrase.
    """

    normalized_fragments = [
        fragment.strip().lower()
        for fragment in text_fragments
        if fragment.strip()
    ]

    return any(
        any(
            fragment in item.text.lower()
            for fragment in normalized_fragments
        )
        for item in _evidence_items(signals)
    )


def _filter_alternatives(
    result: RuleDetectionResult,
    allowed_rules: set[str],
) -> RuleDetectionResult:
    """
    Remove alternative diagnoses that are not mapped to the selected problem.
    """

    filtered_alternatives = [
        code.strip().upper()
        for code in result.alternative_misconception_codes
        if code.strip().upper() in allowed_rules
    ]

    if filtered_alternatives == result.alternative_misconception_codes:
        return result

    return RuleDetectionResult(
        state=result.state,
        misconception_code=result.misconception_code,
        confidence=result.confidence,
        evidence=result.evidence,
        alternative_misconception_codes=filtered_alternatives,
        decision_reason=result.decision_reason,
        next_action=result.next_action,
    )


def _insufficient_result(
    *,
    evidence: list[RuleEvidence],
    reason: str,
) -> RuleDetectionResult:
    """
    Return a valid non-diagnostic result.

    ASK_CLARIFICATION is part of DiagnosisNextAction. Do not return unsupported
    strings such as "request_more_evidence", because Pydantic will reject them.
    """

    return RuleDetectionResult(
        state=DiagnosisState.INSUFFICIENT,
        misconception_code=None,
        confidence=0.0,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=reason,
        next_action=DiagnosisNextAction.ASK_CLARIFICATION,
    )


def _weak_or_general_evidence(
    signals: EvidenceSignals,
) -> list[RuleEvidence]:
    """
    Prefer weak diagnostic evidence for an insufficient result, then fall back
    to a small general evidence sample.
    """

    evidence = _evidence_items(signals)

    weak_evidence = [
        item
        for item in evidence
        if item.strength == EvidenceStrength.WEAK
    ]

    if weak_evidence:
        return weak_evidence[:3]

    return evidence[:3]


def _evidence_matching(
    signals: EvidenceSignals,
    text_fragments: list[str],
) -> list[RuleEvidence]:
    """
    Return evidence relevant to the active rule while preserving Sprint 10
    multimodal provenance.

    Rule-specific matches remain the primary evidence. When a speech transcript
    contributed to the attempt, at least one speech-provenance item is retained
    in the returned evidence so the final diagnosis response does not silently
    lose the student's speech channel.
    """

    normalized_fragments = [
        fragment.strip().lower()
        for fragment in text_fragments
        if fragment.strip()
    ]

    evidence = _evidence_items(signals)

    matched = [
        item
        for item in evidence
        if any(
            fragment in item.text.lower()
            for fragment in normalized_fragments
        )
    ]

    selected = list(
        matched[:5]
        if matched
        else evidence[:3]
    )

    speech_evidence = [
        item
        for item in evidence
        if getattr(
            getattr(item, "source", None),
            "value",
            getattr(item, "source", None),
        )
        == "speech_transcript"
    ]

    if speech_evidence and not any(
        getattr(
            getattr(item, "source", None),
            "value",
            getattr(item, "source", None),
        )
        == "speech_transcript"
        for item in selected
    ):
        speech_item = speech_evidence[0]

        if len(selected) < 5:
            selected.append(speech_item)
        elif selected:
            selected[-1] = speech_item
        else:
            selected.append(speech_item)

    return selected
