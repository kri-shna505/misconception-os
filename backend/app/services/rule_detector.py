from __future__ import annotations

from app.schemas.diagnosis import (
    DiagnosisNextAction,
    DiagnosisState,
    EvidenceStrength,
    RuleDetectionResult,
    RuleEvidence,
)
from app.services.evidence_extractor import EvidenceSignals


SUPPORTED_RULE_CODES = {"M1", "M2", "M3"}


def detect_misconception(signals: EvidenceSignals) -> RuleDetectionResult:
    """
    Rule-based misconception detector for Sprint 4.

    Scope:
    - M1: Binary Search on Unsorted Data
    - M2: Missing or Incorrect Recursion Base Case
    - M3: Recursive Call Without Reducing Problem Size

    Important:
    This detector does not guess.
    It only decides based on observable evidence extracted earlier.
    """

    m3_result = _detect_m3_recursive_no_progress(signals)
    if m3_result is not None:
        return m3_result

    m2_result = _detect_m2_missing_base_case(signals)
    if m2_result is not None:
        return m2_result

    m1_result = _detect_m1_binary_search_unsorted(signals)
    if m1_result is not None:
        return m1_result

    return _insufficient_result(
        evidence=_weak_or_general_evidence(signals),
        reason=(
            "No supported misconception had enough observable evidence for a reliable "
            "Sprint 4 rule diagnosis."
        ),
    )


def _detect_m1_binary_search_unsorted(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M1 rule:
    Student uses binary-search reasoning/code on an unsorted input array.
    """

    if not signals.problem_array_is_unsorted:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "Problem input array is not sorted.",
            "Student reasoning mentions binary search",
            "Student code uses a binary-search pattern",
        ],
    )

    has_reasoning_signal = signals.reasoning_mentions_binary_search
    has_code_signal = signals.code_uses_binary_search

    if has_reasoning_signal and has_code_signal:
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M1",
            confidence=0.90,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The problem input is unsorted, and the student uses binary-search "
                "reasoning plus binary-search style code."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    if has_reasoning_signal or has_code_signal:
        return RuleDetectionResult(
            state=DiagnosisState.POSSIBLE,
            misconception_code="M1",
            confidence=0.65,
            evidence=evidence,
            alternative_misconception_codes=[],
            decision_reason=(
                "The problem input is unsorted and the student shows partial binary-search "
                "evidence, but one signal is missing."
            ),
            next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
        )

    return None


def _detect_m2_missing_base_case(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M2 rule:
    Recursive self-call exists, but no clear base case is detected.
    """

    if not signals.recursive_call_detected:
        return None

    if not signals.missing_base_case:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "Recursive self-call detected",
            "no clear base-case condition was detected",
        ],
    )

    return RuleDetectionResult(
        state=DiagnosisState.CONFIDENT,
        misconception_code="M2",
        confidence=0.86,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=(
            "The code contains a recursive self-call, but the extractor did not find "
            "a clear stopping condition/base case."
        ),
        next_action=DiagnosisNextAction.SHOW_HINT,
    )


def _detect_m3_recursive_no_progress(
    signals: EvidenceSignals,
) -> RuleDetectionResult | None:
    """
    M3 rule:
    Recursive call exists, but the recursive argument does not reduce.
    Priority:
    M3 is checked before M2 because no-progress recursion is more specific.
    """

    if not signals.recursive_call_detected:
        return None

    evidence = _evidence_matching(
        signals,
        [
            "Recursive self-call detected",
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
            confidence=0.92,
            evidence=evidence,
            alternative_misconception_codes=alternatives,
            decision_reason=(
                "The recursive call appears to reuse the same argument, so the problem "
                "size is not reduced."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    if signals.recursive_call_increasing_argument:
        return RuleDetectionResult(
            state=DiagnosisState.CONFIDENT,
            misconception_code="M3",
            confidence=0.92,
            evidence=evidence,
            alternative_misconception_codes=alternatives,
            decision_reason=(
                "The recursive call appears to increase the argument instead of moving "
                "toward the base case."
            ),
            next_action=DiagnosisNextAction.SHOW_HINT,
        )

    if signals.recursive_call_unknown_progress and not signals.recursive_call_decreasing_argument:
        return RuleDetectionResult(
            state=DiagnosisState.POSSIBLE,
            misconception_code="M3",
            confidence=0.58,
            evidence=evidence,
            alternative_misconception_codes=alternatives,
            decision_reason=(
                "A recursive call exists, but the extractor cannot verify that the "
                "recursive argument reduces the problem size."
            ),
            next_action=DiagnosisNextAction.ASK_DIAGNOSTIC_QUESTION,
        )

    return None


def _insufficient_result(
    *,
    evidence: list[RuleEvidence],
    reason: str,
) -> RuleDetectionResult:
    return RuleDetectionResult(
        state=DiagnosisState.INSUFFICIENT,
        misconception_code=None,
        confidence=0.20,
        evidence=evidence,
        alternative_misconception_codes=[],
        decision_reason=reason,
        next_action=DiagnosisNextAction.ASK_CLARIFICATION,
    )


def _weak_or_general_evidence(signals: EvidenceSignals) -> list[RuleEvidence]:
    weak_evidence = [
        item for item in signals.evidence if item.strength == EvidenceStrength.WEAK
    ]

    if weak_evidence:
        return weak_evidence

    return signals.evidence[:3]


def _evidence_matching(
    signals: EvidenceSignals,
    text_fragments: list[str],
) -> list[RuleEvidence]:
    matched: list[RuleEvidence] = []

    for item in signals.evidence:
        item_text = item.text.lower()

        if any(fragment.lower() in item_text for fragment in text_fragments):
            matched.append(item)

    return matched or signals.evidence[:3]