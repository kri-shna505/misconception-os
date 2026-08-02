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


SUPPORTED_RULE_CODES = frozenset({"M1", "M2", "M3"})


def detect_misconception(
    signals: EvidenceSignals,
    allowed_rule_codes: Iterable[str] | None = None,
) -> RuleDetectionResult:
    """
    Detect a supported misconception from already-extracted evidence.

    Sprint 4 supported rules:
    - M1: Binary Search on Unsorted Data
    - M2: Missing or Incorrect Recursion Base Case
    - M3: Recursive Call Without Reducing Problem Size

    Cross-topic protection:
    Only rules mapped to the selected problem are evaluated when
    ``allowed_rule_codes`` is supplied.

    Backward compatibility:
    When ``allowed_rule_codes`` is None, all currently supported rules are
    evaluated.

    This function never inspects raw source code directly. It relies on
    EvidenceSignals produced by evidence_extractor.py.
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
    has_strong_evidence = any(
        item.strength == EvidenceStrength.STRONG
        for item in signals.evidence
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
                    "unsorted array."
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
                "reduces the recursive argument toward termination."
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

    weak_evidence = [
        item
        for item in signals.evidence
        if item.strength == EvidenceStrength.WEAK
    ]

    if weak_evidence:
        return weak_evidence[:3]

    return signals.evidence[:3]


def _evidence_matching(
    signals: EvidenceSignals,
    text_fragments: list[str],
) -> list[RuleEvidence]:
    """
    Return only evidence relevant to the active rule.

    If no exact fragment matches, return a limited evidence sample rather than
    the whole evidence list.
    """

    normalized_fragments = [
        fragment.strip().lower()
        for fragment in text_fragments
        if fragment.strip()
    ]

    matched = [
        item
        for item in signals.evidence
        if any(
            fragment in item.text.lower()
            for fragment in normalized_fragments
        )
    ]

    return matched[:5] if matched else signals.evidence[:3]