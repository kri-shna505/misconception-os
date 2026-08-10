from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any

from app.schemas.diagnosis import (
    EvidenceSource,
    EvidenceStrength,
    RuleEvidence,
)


@dataclass(frozen=True)
class EvidenceSignals:
    evidence: list[RuleEvidence]

    problem_array: list[int | float] | None
    problem_array_is_unsorted: bool

    reasoning_mentions_binary_search: bool
    code_uses_binary_search: bool
    code_uses_linear_search: bool

    recursive_call_detected: bool
    recursive_function_name: str | None
    base_case_detected: bool
    missing_base_case: bool

    recursive_call_same_argument: bool
    recursive_call_increasing_argument: bool
    recursive_call_decreasing_argument: bool
    recursive_call_unknown_progress: bool

    weak_submission: bool

    # Sprint 8 (M4 / M5)
    parameter_reassignment_claims_caller_mutation: bool
    pass_by_value_confusion_detected: bool
    swap_uses_only_local_reassignment: bool
    pointer_based_swap_detected: bool
    return_based_swap_detected: bool
    correct_parameter_semantics_understood: bool

    stack_heap_confusion_detected: bool
    single_stack_frame_claim_detected: bool
    locals_survive_return_claim_detected: bool
    recursive_locals_on_heap_claim_detected: bool

    # Sprint 9 M5 corrective-understanding signals
    separate_stack_frames_understood: bool
    locals_end_with_frame_understood: bool
    stack_heap_distinction_understood: bool


def extract_evidence(attempt: Any, problem: Any) -> EvidenceSignals:
    """
    Extract observable evidence from a saved student attempt and its seeded problem.

    This service does not decide the final misconception.
    It only produces evidence/signals that rule detectors can use later.

    Important protections:
    - A normal call made outside a function is not treated as recursion.
    - Statements that explicitly reject binary search on unsorted data are not
      treated as evidence that the student is using binary search incorrectly.
    """

    final_answer = _safe_text(_get_attr(attempt, "final_answer"))
    written_reasoning = _safe_text(_get_attr(attempt, "written_reasoning"))
    source_code = _safe_text(_get_attr(attempt, "source_code"))
    speech_transcript = _safe_text(_get_attr(attempt, "speech_transcript"))

    problem_statement = _safe_text(_get_attr(problem, "statement"))
    rule_context = _safe_rule_context(_get_attr(problem, "rule_context"))

    combined_reasoning = " ".join(
        part
        for part in [final_answer, written_reasoning, speech_transcript]
        if part.strip()
    )

    evidence: list[RuleEvidence] = []

    problem_array = _extract_problem_array(rule_context, problem_statement)
    problem_array_is_unsorted = bool(problem_array and _is_unsorted(problem_array))

    if problem_array:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.PROBLEM,
                strength=EvidenceStrength.MEDIUM,
                text=f"Problem input array detected: {problem_array}.",
                metadata={"array": problem_array},
            )
        )

    if problem_array_is_unsorted:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.PROBLEM,
                strength=EvidenceStrength.STRONG,
                text="Problem input array is not sorted.",
                metadata={"array": problem_array},
            )
        )

    reasoning_mentions_binary_search = _reasoning_uses_binary_search(
        combined_reasoning
    )

    if reasoning_mentions_binary_search:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student reasoning proposes or endorses binary search or "
                    "O(log n) search for the current input."
                ),
                metadata={
                    "matched_area": (
                        "final_answer/written_reasoning/speech_transcript"
                    )
                },
            )
        )
    elif _explicitly_rejects_binary_search(combined_reasoning):
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.MEDIUM,
                text=(
                    "Student explicitly states that binary search should not be "
                    "used directly on the unsorted input."
                ),
                metadata={"binary_search_rejected": True},
            )
        )

    code_uses_binary_search = _code_uses_binary_search(source_code)

    if code_uses_binary_search:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student code uses a binary-search pattern with "
                    "left/right/mid style logic."
                ),
                metadata={"pattern": "binary_search"},
            )
        )

    code_uses_linear_search = _code_uses_linear_search(source_code)

    if code_uses_linear_search:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student code scans the array sequentially using a "
                    "linear-search pattern."
                ),
                metadata={
                    "pattern": "linear_search",
                    "sequential_scan": True,
                },
            )
        )

    recursive_info = _extract_recursive_info(source_code)

    if recursive_info["recursive_call_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Recursive self-call detected inside function "
                    f"'{recursive_info['function_name']}'."
                ),
                metadata={
                    "function_name": recursive_info["function_name"]
                },
            )
        )

    if recursive_info["base_case_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text="A recursion base-case condition is present in the source code.",
                metadata={"base_case_detected": True},
            )
        )

    if (
        recursive_info["recursive_call_detected"]
        and not recursive_info["base_case_detected"]
    ):
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Recursive call is present, but no clear base-case "
                    "condition was detected."
                ),
                metadata={"missing_base_case": True},
            )
        )

    if recursive_info["same_argument"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Recursive call appears to reuse the same argument "
                    "without reducing the problem size."
                ),
                metadata={"progress": "same_argument"},
            )
        )

    if recursive_info["increasing_argument"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Recursive call appears to increase the argument "
                    "instead of reducing it."
                ),
                metadata={"progress": "increasing_argument"},
            )
        )

    if recursive_info["decreasing_argument"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.MEDIUM,
                text="Recursive call appears to reduce the argument.",
                metadata={"progress": "decreasing_argument"},
            )
        )

    if recursive_info["unknown_progress"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.WEAK,
                text=(
                    "Recursive call was detected, but argument progress "
                    "is unclear."
                ),
                metadata={"progress": "unknown"},
            )
        )

    m4_signals = _extract_m4_signals(
        combined_reasoning=combined_reasoning,
        source_code=source_code,
    )

    if m4_signals["parameter_reassignment_claims_caller_mutation"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student claims that changing local parameters changes "
                    "the caller variables automatically."
                ),
                metadata={
                    "parameter_reassignment_claims_caller_mutation": True,
                },
            )
        )

    if m4_signals["pass_by_value_confusion_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student reasoning indicates that pass by value changes "
                    "the original variable or that parameters are references "
                    "by default."
                ),
                metadata={
                    "pass_by_value_confusion_detected": True,
                },
            )
        )

    if m4_signals["swap_uses_only_local_reassignment"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Swap function only reassigns local parameters; no "
                    "caller-visible mutation mechanism was detected."
                ),
                metadata={
                    "swap_uses_only_local_reassignment": True,
                    "pointer_dereference_detected": False,
                    "returned_swapped_values": False,
                },
            )
        )

    if m4_signals["pointer_based_swap_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Swap implementation uses pointers, passes addresses, "
                    "and dereferences the pointers to modify caller variables."
                ),
                metadata={
                    "pointer_based_swap_detected": True,
                },
            )
        )

    if m4_signals["return_based_swap_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Swap implementation returns the swapped values to the "
                    "caller."
                ),
                metadata={
                    "return_based_swap_detected": True,
                },
            )
        )

    if m4_signals["correct_parameter_semantics_understood"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student correctly explains pass-by-value: local parameter "
                    "changes do not change the caller variables automatically."
                ),
                metadata={
                    "correct_parameter_semantics_understood": True,
                    "caller_variables_remain_unchanged": True,
                },
            )
        )

    m5_signals = _extract_m5_signals(
        combined_reasoning=combined_reasoning,
    )

    if m5_signals["single_stack_frame_claim_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student claims that recursive calls reuse or share a "
                    "single stack frame instead of each active call having "
                    "its own frame."
                ),
                metadata={
                    "stack_heap_confusion_detected": True,
                    "single_stack_frame_claim_detected": True,
                },
            )
        )

    if m5_signals["recursive_locals_on_heap_claim_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Student claims that ordinary recursive local variables "
                    "are stored or remain alive on the heap."
                ),
                metadata={
                    "stack_heap_confusion_detected": True,
                    "recursive_locals_on_heap_claim_detected": True,
                },
            )
        )

    if m5_signals["locals_survive_return_claim_detected"]:
        survival_is_uncertain = bool(
            m5_signals.get(
                "locals_survive_return_uncertainty_detected",
                False,
            )
        )

        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=(
                    EvidenceStrength.MEDIUM
                    if survival_is_uncertain
                    else EvidenceStrength.STRONG
                ),
                text=(
                    "Student is still uncertain whether call-local data can "
                    "survive after the recursive call returns."
                    if survival_is_uncertain
                    else (
                        "Student claims that a call's local variables survive "
                        "after that recursive call returns."
                    )
                ),
                metadata={
                    "stack_heap_confusion_detected": True,
                    "locals_survive_return_claim_detected": True,
                    "residual_uncertainty": survival_is_uncertain,
                },
            )
        )

    if m5_signals["separate_stack_frames_understood"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Each recursive call has its own stack frame."
                ),
                metadata={
                    "m5_corrective_evidence": True,
                    "separate_stack_frames_understood": True,
                },
            )
        )

    if m5_signals["locals_end_with_frame_understood"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text=(
                    "Local variables are removed when the call returns."
                ),
                metadata={
                    "m5_corrective_evidence": True,
                    "locals_end_with_frame_understood": True,
                },
            )
        )

    if m5_signals["stack_heap_distinction_understood"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.MEDIUM,
                text=(
                    "Heap-allocated memory follows different lifetime rules."
                ),
                metadata={
                    "m5_corrective_evidence": True,
                    "stack_heap_distinction_understood": True,
                },
            )
        )

    weak_submission = _is_weak_submission(
        final_answer=final_answer,
        written_reasoning=written_reasoning,
        source_code=source_code,
        speech_transcript=speech_transcript,
    )

    if weak_submission:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.RULE_ENGINE,
                strength=EvidenceStrength.WEAK,
                text=(
                    "Submission contains limited evidence for reliable "
                    "misconception diagnosis."
                ),
                metadata={"weak_submission": True},
            )
        )

    return EvidenceSignals(
        evidence=evidence,
        problem_array=problem_array,
        problem_array_is_unsorted=problem_array_is_unsorted,
        reasoning_mentions_binary_search=reasoning_mentions_binary_search,
        code_uses_binary_search=code_uses_binary_search,
        code_uses_linear_search=code_uses_linear_search,
        recursive_call_detected=recursive_info["recursive_call_detected"],
        recursive_function_name=recursive_info["function_name"],
        base_case_detected=recursive_info["base_case_detected"],
        missing_base_case=(
            recursive_info["recursive_call_detected"]
            and not recursive_info["base_case_detected"]
        ),
        recursive_call_same_argument=recursive_info["same_argument"],
        recursive_call_increasing_argument=recursive_info["increasing_argument"],
        recursive_call_decreasing_argument=recursive_info["decreasing_argument"],
        recursive_call_unknown_progress=recursive_info["unknown_progress"],
        weak_submission=weak_submission,

        # Sprint 8
        parameter_reassignment_claims_caller_mutation=m4_signals[
            "parameter_reassignment_claims_caller_mutation"
        ],
        pass_by_value_confusion_detected=m4_signals[
            "pass_by_value_confusion_detected"
        ],
        swap_uses_only_local_reassignment=m4_signals[
            "swap_uses_only_local_reassignment"
        ],
        pointer_based_swap_detected=m4_signals[
            "pointer_based_swap_detected"
        ],
        return_based_swap_detected=m4_signals[
            "return_based_swap_detected"
        ],
        correct_parameter_semantics_understood=m4_signals[
            "correct_parameter_semantics_understood"
        ],

        stack_heap_confusion_detected=m5_signals[
            "stack_heap_confusion_detected"
        ],
        single_stack_frame_claim_detected=m5_signals[
            "single_stack_frame_claim_detected"
        ],
        locals_survive_return_claim_detected=m5_signals[
            "locals_survive_return_claim_detected"
        ],
        recursive_locals_on_heap_claim_detected=m5_signals[
            "recursive_locals_on_heap_claim_detected"
        ],
        separate_stack_frames_understood=m5_signals[
            "separate_stack_frames_understood"
        ],
        locals_end_with_frame_understood=m5_signals[
            "locals_end_with_frame_understood"
        ],
        stack_heap_distinction_understood=m5_signals[
            "stack_heap_distinction_understood"
        ],
    )



def _extract_m5_signals(
    *,
    combined_reasoning: str,
) -> dict[str, bool]:
    """
    Extract deterministic M5 stack-vs-heap signals.

    Sprint 9 behavior:
    - detect affirmative misconception claims;
    - suppress misconception claims when explicitly corrected;
    - emit positive understanding signals so corrected retries can become
      NO_MISCONCEPTION instead of INSUFFICIENT.
    """

    normalized = re.sub(
        r"\s+",
        " ",
        combined_reasoning.lower(),
    ).strip()

    if not normalized:
        return {
            "stack_heap_confusion_detected": False,
            "single_stack_frame_claim_detected": False,
            "locals_survive_return_claim_detected": False,
            "recursive_locals_on_heap_claim_detected": False,
            "locals_survive_return_uncertainty_detected": False,
            "separate_stack_frames_understood": False,
            "locals_end_with_frame_understood": False,
            "stack_heap_distinction_understood": False,
        }

    correct_frame_patterns = [
        r"\beach\s+(?:active\s+)?recursive\s+(?:call|invocation)\s+(?:has|gets|creates?)\s+(?:its\s+)?own\s+stack\s+frame\b",
        r"\bevery\s+(?:active\s+)?recursive\s+(?:call|invocation)\s+(?:has|gets|creates?)\s+(?:its\s+)?own\s+stack\s+frame\b",
        r"\brecursive\s+(?:calls|invocations)\s+(?:have|get|create)\s+(?:their\s+)?(?:own|separate)\s+stack\s+frames?\b",
        r"\bseparate\s+(?:active\s+)?stack\s+frames?\b",
        r"\bone\s+stack\s+frame\s+per\s+(?:active\s+)?recursive\s+call\b",
    ]

    frame_rejection_patterns = [
        r"\brecursive\s+calls?\s+(?:do\s+not|don't|does\s+not|doesn't|cannot|can't|never)\s+(?:reuse|share|use)\s+(?:the\s+)?(?:same|one|single)\s+stack\s+frame\b",
        r"\b(?:do\s+not|don't|does\s+not|doesn't|cannot|can't|never)\s+share\s+(?:one|the\s+same|a\s+single)\s+stack\s+frame\b",
    ]

    separate_stack_frames_understood = (
        any(re.search(pattern, normalized) for pattern in correct_frame_patterns)
        or any(re.search(pattern, normalized) for pattern in frame_rejection_patterns)
    )

    single_patterns = [
        r"\b(?:all|every|each)?\s*recursive\s+calls?\s+(?:reuse|reuses|share|shares|use|uses)\s+(?:the\s+)?(?:same|one|single)\s+stack\s+frame\b",
        r"\b(?:only|just)\s+one\s+stack\s+frame\b",
        r"\bsame\s+stack\s+frame\s+(?:is\s+)?(?:reused|shared)\b",
    ]

    single = (
        not separate_stack_frames_understood
        and any(_affirmative_match(pattern, normalized) for pattern in single_patterns)
    )

    local_lifetime_correct_patterns = [
        r"\b(?:local\s+variables?|locals?)\s+(?:belong|belongs)\s+to\s+(?:that|the|each)\s+(?:call(?:'s)?\s+)?stack\s+frame\b",
        r"\b(?:local\s+variables?|locals?)\s+(?:are\s+)?(?:removed|destroyed|discarded)\s+when\s+(?:the\s+)?(?:recursive\s+)?call\s+returns?\b",
        r"\b(?:local\s+variables?|locals?)\s+(?:disappear|cease\s+to\s+exist|no\s+longer\s+exist)\s+when\s+(?:the\s+)?(?:recursive\s+)?call\s+returns?\b",
        r"\bwhen\s+(?:the\s+)?(?:recursive\s+)?call\s+returns?\b.{0,80}\b(?:local\s+variables?|locals?)\b.{0,40}\b(?:are\s+removed|are\s+destroyed|disappear|cease\s+to\s+exist|no\s+longer\s+exist)\b",
        r"\b(?:stack\s+frame|frame)\s+(?:is\s+)?(?:removed|popped|destroyed)\s+when\s+(?:the\s+)?call\s+returns?\b",
    ]

    local_lifetime_rejection_patterns = [
        r"\b(?:local\s+variables?|locals?|stack\s+variables?)\b.{0,80}\b(?:do\s+not|don't|does\s+not|doesn't|cannot|can't|never|no\s+longer)\b.{0,40}\b(?:remain|remains|survive|survives|stay|stays|persist|persists|exist)\b.{0,60}\b(?:after|when)\b.{0,40}\b(?:return|returns|call\s+returns|function\s+returns)\b",
    ]

    locals_end_with_frame_understood = (
        any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in local_lifetime_correct_patterns)
        or any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in local_lifetime_rejection_patterns)
    )

    survive_patterns = [
        r"\b(?:local\s+variables?|locals?|stack\s+variables?|local\s+data)\b.{0,90}\b(?:remain|remains|survive|survives|stay|stays|persist|persists)\b.{0,70}\bafter\b.{0,40}\b(?:return|returns|function\s+returns|call\s+returns|recursive\s+call\s+returns)\b",
        r"\b(?:local\s+variables?|locals?|stack\s+variables?|local\s+data)\b.{0,90}\b(?:remain|remains|stay|stays)\b.{0,40}\balive\b.{0,60}\bafter\b.{0,40}\b(?:return|returns)\b",
    ]

    affirmative_survival_claim = (
        not locals_end_with_frame_understood
        and any(
            _affirmative_match(pattern, normalized, flags=re.DOTALL)
            for pattern in survive_patterns
        )
    )

    # Sprint 9 improving-state support:
    # Correcting the stack-frame model while still expressing uncertainty
    # about call-local lifetime is weaker than a direct misconception, but it
    # is still unresolved M5 evidence.  This lets the diagnosis fall to
    # POSSIBLE instead of staying CONFIDENT or jumping to NO_MISCONCEPTION.
    survival_uncertainty_patterns = [
        r"\b(?:still\s+)?(?:unsure|uncertain|not\s+sure|unclear)\b.{0,120}\b(?:local\s+variables?|locals?|local\s+data|data\s+associated\s+with\s+(?:that|the)\s+call)\b.{0,120}\b(?:could|might|may)\b.{0,35}\b(?:remain|survive|persist|stay)\b.{0,80}\b(?:after|afterward|afterwards|once)\b.{0,60}\b(?:return|returns|call\s+returns|recursive\s+call\s+returns|frame\s+ends?)\b",
        r"\b(?:local\s+variables?|locals?|local\s+data|data\s+associated\s+with\s+(?:that|the)\s+call)\b.{0,120}\b(?:could|might|may)\b.{0,35}\b(?:remain|survive|persist|stay)\b.{0,80}\b(?:after|afterward|afterwards)\b.{0,60}\b(?:return|returns)\b.{0,100}\b(?:unsure|uncertain|not\s+sure|unclear)\b",
    ]

    locals_survive_return_uncertainty_detected = any(
        re.search(
            pattern,
            normalized,
            flags=re.DOTALL,
        )
        for pattern in survival_uncertainty_patterns
    )

    survive = (
        affirmative_survival_claim
        or locals_survive_return_uncertainty_detected
    )

    heap_correct_patterns = [
        r"\b(?:ordinary\s+)?(?:recursive\s+)?local\s+variables?\b.{0,70}\b(?:are\s+not|aren't|do\s+not|don't|never)\b.{0,35}\b(?:stored|allocated|kept)\b.{0,35}\bheap\b",
        r"\b(?:local\s+variables?|locals?)\b.{0,60}\b(?:are\s+on|live\s+on|stored\s+on|stored\s+in)\s+the\s+stack\b",
        r"\bheap(?:-allocated)?\s+memory\b.{0,70}\b(?:different|separate)\b.{0,45}\blifetime\b",
        r"\bheap\s+memory\b.{0,70}\b(?:different|separate)\b.{0,45}\blifetime\b",
        r"\bstack\s+and\s+heap\b.{0,70}\b(?:different|distinct|separate)\b.{0,45}\b(?:roles|purposes|lifetime|lifetimes|storage)\b",
    ]

    heap_rejection_patterns = [
        r"\b(?:recursive\s+)?local\s+variables?\b.{0,60}\b(?:are\s+not|aren't|do\s+not|don't|does\s+not|doesn't|never)\b.{0,40}\b(?:stored|allocated|kept|remain|remains|stay|stays|live|alive)\b.{0,50}\bheap\b",
        r"\b(?:recursive\s+)?local\s+variables?\b.{0,80}\b(?:not|never)\b.{0,25}\bheap\b",
        r"\bordinary\s+local\s+variables?\b.{0,80}\b(?:not|never)\b.{0,30}\bheap\b",
    ]

    stack_heap_distinction_understood = (
        any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in heap_correct_patterns)
        or any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in heap_rejection_patterns)
    )

    heap_patterns = [
        r"\b(?:recursive\s+)?local\s+variables?\b.{0,80}\b(?:stored|allocated|kept|remain|remains|stay|stays|live|alive)\b.{0,50}\bheap\b",
        r"\blocals?\b.{0,70}\b(?:stored|allocated|kept|remain|remains|stay|stays|live|alive)\b.{0,50}\bheap\b",
        r"\bfunction\s+call\s+frames?\b.{0,50}\bheap\b",
    ]

    heap = (
        not stack_heap_distinction_understood
        and any(
            _affirmative_match(pattern, normalized, flags=re.DOTALL)
            for pattern in heap_patterns
        )
    )

    generic_same = (
        not stack_heap_distinction_understood
        and _affirmative_match(
            r"\bstack\s+and\s+heap\s+(?:are|is)\s+(?:the\s+)?same\b",
            normalized,
        )
    )

    return {
        "stack_heap_confusion_detected": generic_same or single or heap or survive,
        "single_stack_frame_claim_detected": single,
        "locals_survive_return_claim_detected": survive,
        "recursive_locals_on_heap_claim_detected": heap,
        "locals_survive_return_uncertainty_detected": (
            locals_survive_return_uncertainty_detected
        ),
        "separate_stack_frames_understood": separate_stack_frames_understood,
        "locals_end_with_frame_understood": locals_end_with_frame_understood,
        "stack_heap_distinction_understood": stack_heap_distinction_understood,
    }

def _affirmative_match(
    pattern: str,
    text: str,
    *,
    flags: int = 0,
) -> bool:
    """
    Match an M5 misconception pattern only when it is not locally negated.

    This is intentionally narrow. It prevents false positives from corrected
    retry statements such as:
    - "recursive calls do not share one stack frame";
    - "local variables are not stored on the heap";
    - "locals do not remain alive after the call returns".
    """

    negation_pattern = re.compile(
        r"\\b(?:not|no|never|cannot|can't|do\\s+not|don't|does\\s+not|doesn't|"
        r"are\\s+not|aren't|is\\s+not|isn't|will\\s+not|won't)\\b",
        flags=re.IGNORECASE,
    )

    for match in re.finditer(
        pattern,
        text,
        flags=flags,
    ):
        window_start = max(
            0,
            match.start() - 45,
        )
        local_prefix = text[
            window_start:match.start()
        ]

        if negation_pattern.search(
            local_prefix
        ):
            continue

        return True

    return False


def _extract_m4_signals(
    *,
    combined_reasoning: str,
    source_code: str,
) -> dict[str, bool]:
    """Extract M4 pass-by-value and swap-mechanism signals.

    Matching is intentionally independent of specific variable names. The
    implementation scopes return and pointer checks to the swap function so
    ``return 0`` in ``main`` cannot be mistaken for a return-based swap.
    """

    normalized_reasoning = re.sub(
        r"\s+",
        " ",
        combined_reasoning.lower(),
    ).strip()

    parameter_claim_patterns = [
        r"(?:changing|reassigning|modifying|swapping).{0,60}(?:parameter|x|y|local variable).{0,80}(?:original|caller).{0,50}(?:change|swap|modify|affect)",
        r"(?:original|caller).{0,60}(?:variable|value).{0,50}(?:change|swap|modify|affect).{0,60}(?:automatically|directly|also|inside the function)?",
        r"(?:x|y).{0,40}(?:changed|swapped|reassigned).{0,70}(?:inside|in) the (?:swap )?function.{0,70}(?:original|caller).{0,40}(?:change|swap|modify)",
        r"local (?:parameter|assignment|reassignment|change).{0,70}(?:changes|modifies|swaps|affects).{0,50}(?:caller|original)",
        r"(?:function|swap).{0,50}(?:reassigns|changes|swaps).{0,60}(?:parameters?|x|y).{0,70}(?:caller|original).{0,50}(?:changes?|swaps?|modified)",
        r"(?:caller|original).{0,50}(?:changes?|swaps?|modified).{0,70}(?:because|when|after).{0,60}(?:parameter|x|y).{0,40}(?:reassigned|changed|swapped)",
    ]

    pass_by_value_confusion_patterns = [
        r"pass(?:ed)? by value.{0,40}(?:changes|modifies|swaps).{0,30}(?:original|caller)",
        r"parameters? (?:are|act as) references? by default",
        r"(?:c|the language).{0,30}passes? parameters? by reference by default",
    ]

    parameter_claim = any(
        re.search(pattern, normalized_reasoning)
        for pattern in parameter_claim_patterns
    )
    pass_by_value_confusion = any(
        re.search(pattern, normalized_reasoning)
        for pattern in pass_by_value_confusion_patterns
    )

    correct_indirection_explanation = _contains_any(
        normalized_reasoning,
        [
            "uses pointers",
            "use pointers",
            "passes addresses",
            "pass addresses",
            "dereferences the pointers",
            "dereference the pointers",
            "modify caller variables through pointers",
            "modifies caller variables through pointers",
            "return the swapped values",
            "returns the swapped values",
            "pass by value does not change the original",
            "passed by value does not change the original",
            "pass by value does not change the caller",
            "local parameters do not change the caller variables",
            "local copies do not change the caller variables",
            "changing local parameters does not change the original variables",
            "changing the parameters does not change the original variables",
            "caller variables remain unchanged",
            "original variables remain unchanged",
        ],
    )

    correct_parameter_semantics_understood = (
        correct_indirection_explanation
        and not parameter_claim
        and not pass_by_value_confusion
    )

    python_signals = _extract_python_swap_signals(source_code)

    if python_signals is not None:
        return_based = python_signals[
            "return_based_swap_detected"
        ]
        local_reassignment = python_signals[
            "swap_uses_only_local_reassignment"
        ]

        return {
            "parameter_reassignment_claims_caller_mutation": (
                parameter_claim
                and not correct_indirection_explanation
                and not return_based
            ),
            "pass_by_value_confusion_detected": pass_by_value_confusion,
            "swap_uses_only_local_reassignment": local_reassignment,
            "pointer_based_swap_detected": False,
            "return_based_swap_detected": return_based,
            "correct_parameter_semantics_understood": (
                correct_parameter_semantics_understood
            ),
        }

    swap_body, parameter_names = _extract_c_swap_function(
        source_code
    )

    if not swap_body:
        return {
            "parameter_reassignment_claims_caller_mutation": parameter_claim,
            "pass_by_value_confusion_detected": pass_by_value_confusion,
            "swap_uses_only_local_reassignment": False,
            "pointer_based_swap_detected": False,
            "return_based_swap_detected": False,
            "correct_parameter_semantics_understood": (
                correct_parameter_semantics_understood
            ),
        }

    normalized_body = _strip_c_comments(swap_body)

    pointer_based = _detect_pointer_swap(
        source_code=source_code,
        swap_body=normalized_body,
        parameter_names=parameter_names,
    )
    return_based = _detect_return_based_swap(
        swap_body=normalized_body,
    )
    local_reassignment = _detect_local_parameter_swap(
        swap_body=normalized_body,
        parameter_names=parameter_names,
    )

    return {
        "parameter_reassignment_claims_caller_mutation": (
            parameter_claim
            and not correct_indirection_explanation
            and not pointer_based
            and not return_based
        ),
        "pass_by_value_confusion_detected": pass_by_value_confusion,
        "swap_uses_only_local_reassignment": (
            local_reassignment
            and not pointer_based
            and not return_based
        ),
        "pointer_based_swap_detected": pointer_based,
        "return_based_swap_detected": return_based,
        "correct_parameter_semantics_understood": (
            correct_parameter_semantics_understood
            or pointer_based
            or return_based
        ),
    }



def _extract_python_swap_signals(
    source_code: str,
) -> dict[str, bool] | None:
    """Return structured M4 signals for a Python ``swap`` function.

    A tuple/list return such as ``return b, a`` is treated as a valid
    return-based swap. Local-only reassignment such as ``a = b`` and
    ``b = temp`` is treated as caller-invisible mutation.
    """

    code = source_code.strip()
    if not code:
        return None

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    function_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.lower() == "swap"
        ),
        None,
    )

    if function_node is None:
        return None

    parameter_names = [
        argument.arg
        for argument in [
            *function_node.args.posonlyargs,
            *function_node.args.args,
        ]
        if argument.arg not in {"self", "cls"}
    ]

    if len(parameter_names) < 2:
        return {
            "swap_uses_only_local_reassignment": False,
            "return_based_swap_detected": False,
        }

    first, second = parameter_names[:2]

    return_based = False
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Return) or node.value is None:
            continue

        if isinstance(node.value, (ast.Tuple, ast.List)):
            returned_names = [
                item.id
                for item in node.value.elts
                if isinstance(item, ast.Name)
            ]
            if (
                len(returned_names) >= 2
                and first in returned_names
                and second in returned_names
            ):
                return_based = True
                break

        elif isinstance(node.value, ast.Name) and node.value.id not in {"None"}:
            return_based = True
            break

    assignments: list[tuple[str, str]] = []
    tuple_swap = False

    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign):
            continue

        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], (ast.Tuple, ast.List))
            and isinstance(node.value, (ast.Tuple, ast.List))
        ):
            left_names = [
                item.id
                for item in node.targets[0].elts
                if isinstance(item, ast.Name)
            ]
            right_names = [
                item.id
                for item in node.value.elts
                if isinstance(item, ast.Name)
            ]
            if left_names[:2] == [first, second] and right_names[:2] == [second, first]:
                tuple_swap = True

        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Name)
        ):
            assignments.append((node.targets[0].id, node.value.id))

    temporary_captures_parameter = any(
        left not in {first, second} and right in {first, second}
        for left, right in assignments
    )
    first_receives_second = (first, second) in assignments
    second_receives_something = any(
        left == second for left, _ in assignments
    )

    local_reassignment = tuple_swap or (
        temporary_captures_parameter
        and first_receives_second
        and second_receives_something
    )

    return {
        "swap_uses_only_local_reassignment": (
            local_reassignment and not return_based
        ),
        "return_based_swap_detected": return_based,
    }

def _extract_c_swap_function(
    source_code: str,
) -> tuple[str, list[str]]:
    """Return the body and parameter names of a C-like swap function."""

    if not source_code.strip():
        return "", []

    signature = re.search(
        r"\b(?:void|int|long|short|float|double|[A-Za-z_]\w*)"
        r"\s+swap\s*\((?P<params>[^)]*)\)\s*\{",
        source_code,
        flags=re.IGNORECASE,
    )

    if signature is None:
        return "", []

    open_brace = source_code.find("{", signature.start())
    if open_brace < 0:
        return "", []

    depth = 0
    close_brace = -1

    for index in range(open_brace, len(source_code)):
        character = source_code[index]

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                close_brace = index
                break

    if close_brace < 0:
        return "", []

    parameter_names: list[str] = []

    for raw_parameter in signature.group("params").split(","):
        parameter = raw_parameter.strip()
        if not parameter or parameter == "void":
            continue

        identifiers = re.findall(
            r"[A-Za-z_]\w*",
            parameter,
        )
        if identifiers:
            parameter_names.append(identifiers[-1])

    return (
        source_code[open_brace + 1 : close_brace],
        parameter_names,
    )


def _strip_c_comments(source_code: str) -> str:
    without_block_comments = re.sub(
        r"/\*.*?\*/",
        " ",
        source_code,
        flags=re.DOTALL,
    )
    return re.sub(
        r"//[^\n]*",
        " ",
        without_block_comments,
    )


def _detect_local_parameter_swap(
    *,
    swap_body: str,
    parameter_names: list[str],
) -> bool:
    if len(parameter_names) < 2:
        return False

    first = re.escape(parameter_names[0])
    second = re.escape(parameter_names[1])

    assignments = [
        match.groups()
        for match in re.finditer(
            r"\b([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*;",
            swap_body,
        )
    ]

    if not assignments:
        return False

    first_receives_second = any(
        left == parameter_names[0]
        and right == parameter_names[1]
        for left, right in assignments
    )
    second_is_assigned = any(
        left == parameter_names[1]
        for left, _ in assignments
    )
    temporary_captures_parameter = any(
        left not in parameter_names
        and right in parameter_names
        for left, right in assignments
    )

    direct_three_step_pattern = bool(
        re.search(
            rf"\b(?P<temp>[A-Za-z_]\w*)\s*=\s*{first}\s*;"
            rf".*?\b{first}\s*=\s*{second}\s*;"
            rf".*?\b{second}\s*=\s*(?P=temp)\s*;",
            swap_body,
            flags=re.DOTALL,
        )
        or re.search(
            rf"\b(?P<temp>[A-Za-z_]\w*)\s*=\s*{second}\s*;"
            rf".*?\b{second}\s*=\s*{first}\s*;"
            rf".*?\b{first}\s*=\s*(?P=temp)\s*;",
            swap_body,
            flags=re.DOTALL,
        )
    )

    return direct_three_step_pattern or (
        first_receives_second
        and second_is_assigned
        and temporary_captures_parameter
    )


def _detect_pointer_swap(
    *,
    source_code: str,
    swap_body: str,
    parameter_names: list[str],
) -> bool:
    if len(parameter_names) < 2:
        return False

    first = re.escape(parameter_names[0])
    second = re.escape(parameter_names[1])

    has_pointer_parameters = bool(
        re.search(
            r"\bswap\s*\([^)]*\*[^,)]*,[^)]*\*",
            source_code,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    dereferences_both = bool(
        re.search(rf"\*\s*{first}\b", swap_body)
        and re.search(rf"\*\s*{second}\b", swap_body)
    )
    passes_addresses = bool(
        re.search(
            r"\bswap\s*\(\s*&\s*[A-Za-z_]\w*\s*,"
            r"\s*&\s*[A-Za-z_]\w*\s*\)",
            source_code,
            flags=re.IGNORECASE,
        )
    )

    return has_pointer_parameters and dereferences_both and passes_addresses


def _detect_return_based_swap(
    *,
    swap_body: str,
) -> bool:
    return bool(
        re.search(
            r"\breturn\b\s+(?!0\s*;|NULL\s*;|nullptr\s*;)"
            r"[^;]+;",
            swap_body,
            flags=re.IGNORECASE,
        )
    )

def _get_attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None

    if isinstance(obj, dict):
        return obj.get(name)

    return getattr(obj, name, None)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()



def _contains_any(
    text: str | None,
    phrases: list[str],
) -> bool:
    """
    Return True when normalized text contains at least one non-empty phrase.

    Matching is case-insensitive. Missing or blank text safely returns False.
    """

    normalized_text = (text or "").strip().lower()

    if not normalized_text:
        return False

    return any(
        phrase.strip().lower() in normalized_text
        for phrase in phrases
        if phrase.strip()
    )


def _safe_rule_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}

        if isinstance(parsed, dict):
            return parsed

    return {}


def _extract_problem_array(
    rule_context: dict[str, Any],
    problem_statement: str,
) -> list[int | float] | None:
    possible_keys = [
        "array",
        "input_array",
        "given_array",
        "values",
        "numbers",
        "arr",
    ]

    for key in possible_keys:
        value = rule_context.get(key)

        parsed = _coerce_number_list(value)
        if parsed:
            return parsed

    statement_array = _extract_array_from_text(problem_statement)
    if statement_array:
        return statement_array

    return None


def _coerce_number_list(value: Any) -> list[int | float] | None:
    if not isinstance(value, list):
        return None

    result: list[int | float] = []

    for item in value:
        if isinstance(item, bool):
            return None

        if isinstance(item, (int, float)):
            result.append(item)
            continue

        if isinstance(item, str):
            try:
                number = float(item) if "." in item else int(item)
            except ValueError:
                return None

            result.append(number)
            continue

        return None

    return result or None


def _extract_array_from_text(text: str) -> list[int | float] | None:
    match = re.search(r"\[([^\]]+)\]", text)

    if not match:
        return None

    raw_items = match.group(1).split(",")
    result: list[int | float] = []

    for raw_item in raw_items:
        item = raw_item.strip()

        if not item:
            return None

        try:
            number = float(item) if "." in item else int(item)
        except ValueError:
            return None

        result.append(number)

    return result or None


def _is_unsorted(values: list[int | float]) -> bool:
    if len(values) < 2:
        return False

    return any(
        values[index] > values[index + 1]
        for index in range(len(values) - 1)
    )


def _contains_binary_search_term(text: str) -> bool:
    normalized = text.lower()

    patterns = [
        r"\bbinary[\s-]+search\b",
        r"\bo\s*\(\s*log\s*n\s*\)",
        r"\bologn\b",
        r"\blog\s*n\b",
        r"\bdivide\s+and\s+conquer\s+search\b",
    ]

    return any(re.search(pattern, normalized) for pattern in patterns)


def _explicitly_rejects_binary_search(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    rejection_patterns = [
        r"binary[\s-]+search.{0,80}(should\s+not|must\s+not|cannot|can't|not\s+valid|not\s+appropriate|not\s+correct|will\s+not\s+work)",
        r"(should\s+not|must\s+not|cannot|can't|do\s+not|avoid).{0,80}binary[\s-]+search",
        r"binary[\s-]+search.{0,80}(requires|needs).{0,40}sorted",
        r"unsorted.{0,80}(so|therefore|hence).{0,80}(linear\s+search|do\s+not\s+use\s+binary)",
        r"use\s+linear\s+search.{0,100}(instead|because).{0,100}(unsorted|not\s+sorted)",
    ]

    return any(
        re.search(pattern, normalized, flags=re.DOTALL)
        for pattern in rejection_patterns
    )


def _reasoning_uses_binary_search(text: str) -> bool:
    """
    Return True only when the student proposes or endorses binary search.

    Merely mentioning binary search while explaining why it must not be used
    on unsorted input is not misconception evidence.
    """

    if not _contains_binary_search_term(text):
        return False

    if _explicitly_rejects_binary_search(text):
        return False

    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    endorsement_patterns = [
        r"\bi\s+(would|will|can)\s+use\s+binary[\s-]+search\b",
        r"\buse\s+binary[\s-]+search\b",
        r"\bapply\s+binary[\s-]+search\b",
        r"\bperform\s+binary[\s-]+search\b",
        r"\bthe\s+answer\s+is\s+binary[\s-]+search\b",
        r"\btime\s+complexity\s+is\s+o\s*\(\s*log\s*n\s*\)",
        r"\bsearch\s+in\s+o\s*\(\s*log\s*n\s*\)",
    ]

    if any(re.search(pattern, normalized) for pattern in endorsement_patterns):
        return True

    # Preserve the previous detector's behavior for concise student answers
    # such as "binary search" or "O(log n)" when no rejection is present.
    return len(normalized.split()) <= 16


def _code_uses_binary_search(source_code: str) -> bool:
    code = source_code.lower()

    if not code:
        return False

    has_mid = bool(re.search(r"\bmid\b", code))
    has_left_right = (
        bool(re.search(r"\b(left|lo|low)\b", code))
        and bool(re.search(r"\b(right|hi|high)\b", code))
    )
    has_loop = bool(re.search(r"\b(while|for)\b", code))
    has_mid_index = bool(re.search(r"\[[^\]]*mid[^\]]*\]", code))
    has_halving_update = bool(
        re.search(r"(left|lo|low)\s*=\s*mid\s*\+\s*1", code)
        or re.search(r"(right|hi|high)\s*=\s*mid\s*-\s*1", code)
    )

    score = sum(
        [
            has_mid,
            has_left_right,
            has_loop,
            has_mid_index,
            has_halving_update,
        ]
    )

    return score >= 3



def _code_uses_linear_search(source_code: str) -> bool:
    """
    Detect a direct sequential scan over a collection.

    Sprint 9 P1 hardening:
    - Python loops are inspected with AST when possible.
    - C/C++ style ``for`` loops such as
      ``for (int i = 0; i < n; i++)`` with ``arr[i] == target`` are also
      recognized.
    - The detector remains conservative and requires both a sequential scan
      and a target comparison.
    """

    code = source_code.strip()
    if not code:
        return False

    if _code_uses_c_linear_search(code):
        return True

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _code_uses_linear_search_fallback(code)

    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue

        iterable_info = _linear_search_iterable_info(node.iter)
        if iterable_info is None:
            continue

        element_names = set(iterable_info["element_names"])
        index_names = set(iterable_info["index_names"])
        collection_names = set(iterable_info["collection_names"])

        if isinstance(node.target, ast.Name):
            element_names.add(node.target.id)
        elif isinstance(node.target, (ast.Tuple, ast.List)):
            target_names = [
                item.id
                for item in node.target.elts
                if isinstance(item, ast.Name)
            ]
            if len(target_names) >= 2:
                index_names.add(target_names[0])
                element_names.add(target_names[1])

        for child in ast.walk(node):
            if not isinstance(child, ast.If):
                continue

            if not _condition_compares_current_item(
                child.test,
                element_names=element_names,
                index_names=index_names,
                collection_names=collection_names,
            ):
                continue

            if any(
                isinstance(descendant, ast.Return)
                for statement in child.body
                for descendant in ast.walk(statement)
            ):
                return True

    return False


def _code_uses_c_linear_search(source_code: str) -> bool:
    """
    Detect a conventional C/C++ linear search.

    Required evidence:
    - a for-loop whose index advances one element at a time;
    - an indexed collection access using that loop variable;
    - comparison against another value;
    - a return from the matching branch or equivalent immediate success path.
    """

    normalized = _strip_c_comments(source_code)

    for_pattern = re.compile(
        r"\bfor\s*\(\s*"
        r"(?:int\s+|long\s+|size_t\s+|unsigned\s+)?"
        r"(?P<idx>[A-Za-z_]\w*)\s*=\s*0\s*;"
        r"(?P=idx)\s*<\s*(?P<limit>[A-Za-z_]\w*|\d+)\s*;"
        r"(?:(?P=idx)\s*\+\+|\+\+\s*(?P=idx)|(?P=idx)\s*\+=\s*1)"
        r"\s*\)",
        flags=re.IGNORECASE,
    )

    for match in for_pattern.finditer(normalized):
        index_name = re.escape(match.group("idx"))
        loop_start = normalized.find("{", match.end())

        if loop_start < 0:
            continue

        loop_body, _ = _extract_braced_block(
            normalized,
            loop_start,
        )

        if not loop_body:
            continue

        indexed_item_pattern = (
            rf"\b[A-Za-z_]\w*\s*\[\s*{index_name}\s*\]"
        )

        comparison_pattern = re.compile(
            rf"(?:{indexed_item_pattern}\s*(?:==|!=)\s*"
            rf"[A-Za-z_]\w*|"
            rf"[A-Za-z_]\w*\s*(?:==|!=)\s*{indexed_item_pattern})",
            flags=re.IGNORECASE,
        )

        if not comparison_pattern.search(loop_body):
            continue

        if re.search(
            r"\breturn\b\s+[^;]+;",
            loop_body,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def _extract_braced_block(
    source_code: str,
    open_brace: int,
) -> tuple[str, int]:
    """Return the text inside one balanced C/C++ braced block."""

    if (
        open_brace < 0
        or open_brace >= len(source_code)
        or source_code[open_brace] != "{"
    ):
        return "", -1

    depth = 0

    for index in range(
        open_brace,
        len(source_code),
    ):
        character = source_code[index]

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                return (
                    source_code[
                        open_brace + 1:index
                    ],
                    index,
                )

    return "", -1


def _linear_search_iterable_info(iterable: ast.AST) -> dict[str, set[str]] | None:
    element_names: set[str] = set()
    index_names: set[str] = set()
    collection_names: set[str] = set()

    if isinstance(iterable, ast.Name):
        collection_names.add(iterable.id)
        return {
            "element_names": element_names,
            "index_names": index_names,
            "collection_names": collection_names,
        }

    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id == "enumerate"
        and iterable.args
        and isinstance(iterable.args[0], ast.Name)
    ):
        collection_names.add(iterable.args[0].id)
        return {
            "element_names": element_names,
            "index_names": index_names,
            "collection_names": collection_names,
        }

    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id == "range"
        and iterable.args
        and isinstance(iterable.args[0], ast.Call)
        and isinstance(iterable.args[0].func, ast.Name)
        and iterable.args[0].func.id == "len"
        and iterable.args[0].args
        and isinstance(iterable.args[0].args[0], ast.Name)
    ):
        collection_names.add(iterable.args[0].args[0].id)
        return {
            "element_names": element_names,
            "index_names": index_names,
            "collection_names": collection_names,
        }

    return None


def _condition_compares_current_item(
    condition: ast.AST,
    *,
    element_names: set[str],
    index_names: set[str],
    collection_names: set[str],
) -> bool:
    for node in ast.walk(condition):
        if not isinstance(node, ast.Compare):
            continue

        operands = [node.left, *node.comparators]

        has_current_item = any(
            _is_current_linear_search_item(
                operand,
                element_names=element_names,
                index_names=index_names,
                collection_names=collection_names,
            )
            for operand in operands
        )

        has_other_value = any(
            not _is_current_linear_search_item(
                operand,
                element_names=element_names,
                index_names=index_names,
                collection_names=collection_names,
            )
            for operand in operands
        )

        if has_current_item and has_other_value:
            return True

    return False


def _is_current_linear_search_item(
    node: ast.AST,
    *,
    element_names: set[str],
    index_names: set[str],
    collection_names: set[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in element_names

    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id in collection_names
    ):
        if isinstance(node.slice, ast.Name):
            return node.slice.id in index_names

    return False


def _code_uses_linear_search_fallback(source_code: str) -> bool:
    normalized = re.sub(r"\s+", " ", source_code.lower())

    patterns = [
        r"for\s+\w+\s*,\s*\w+\s+in\s+enumerate\s*\([^)]+\).*?"
        r"if\s+\w+\s*==\s*\w+.*?return\s+\w+",
        r"for\s+\w+\s+in\s+[^:]+:.*?"
        r"if\s+\w+\s*==\s*\w+.*?return",
        r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\([^)]+\)\s*\).*?"
        r"if\s+\w+\s*\[\s*\w+\s*\]\s*==\s*\w+.*?return",
        r"for\s*\(\s*(?:int\s+|long\s+|size_t\s+|unsigned\s+)?"
        r"\w+\s*=\s*0\s*;\s*\w+\s*<\s*\w+\s*;"
        r"\s*(?:\w+\+\+|\+\+\w+|\w+\s*\+=\s*1)\s*\).*?"
        r"if\s*\([^)]*\[[^\]]+\][^)]*==[^)]*\).*?return",
    ]

    return any(
        re.search(pattern, normalized, flags=re.DOTALL)
        for pattern in patterns
    )

def _extract_recursive_info(source_code: str) -> dict[str, Any]:
    """
    Extract recursion signals from Python or C/C++ source code.

    Sprint 9 P2/P3 hardening:
    - Python source uses AST analysis.
    - C/C++ source uses a bounded function-body parser.
    - only a self-call inside the corresponding function body counts as
      recursion; ordinary calls from ``main`` are ignored.
    """

    result = _empty_recursive_result()

    code = source_code.strip()
    if not code:
        return result

    c_result = _extract_c_recursive_info(code)

    if c_result is not None:
        return c_result

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _extract_recursive_info_fallback(code)

    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    if not functions:
        return result

    function_node = functions[0]
    function_name = function_node.name
    primary_param = _first_python_param(function_node)

    self_calls = [
        node
        for node in ast.walk(function_node)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == function_name
        and node is not function_node
    ]

    result["function_name"] = function_name

    if not self_calls:
        return result

    result["recursive_call_detected"] = True
    result["base_case_detected"] = _has_python_base_case(
        function_node,
        primary_param,
    )

    if primary_param is None:
        result["unknown_progress"] = True
        return result

    progress_found = False

    for call in self_calls:
        if not call.args:
            result["unknown_progress"] = True
            continue

        progress = _classify_python_recursive_argument(
            call.args[0],
            primary_param,
        )

        if progress == "same_argument":
            result["same_argument"] = True
            progress_found = True
        elif progress == "increasing_argument":
            result["increasing_argument"] = True
            progress_found = True
        elif progress == "decreasing_argument":
            result["decreasing_argument"] = True
            progress_found = True
        else:
            result["unknown_progress"] = True

    if not progress_found and not result["unknown_progress"]:
        result["unknown_progress"] = True

    return result


def _extract_c_recursive_info(
    source_code: str,
) -> dict[str, Any] | None:
    """
    Return structured recursion signals for the first C/C++ function that
    recursively calls itself.

    ``None`` means the source does not look like C/C++ function syntax and the
    caller may continue with Python analysis.
    """

    code = _strip_c_comments(source_code)

    signature_pattern = re.compile(
        r"(?:^|\n)\s*"
        r"(?:static\s+|inline\s+|const\s+|unsigned\s+|signed\s+)*"
        r"(?:void|int|long|short|float|double|char|bool|size_t|"
        r"[A-Za-z_]\w*(?:\s*\*)?)"
        r"\s+(?P<name>[A-Za-z_]\w*)\s*"
        r"\((?P<params>[^;{}()]*)\)\s*\{",
        flags=re.IGNORECASE,
    )

    matches = list(
        signature_pattern.finditer(code)
    )

    if not matches:
        return None

    for signature in matches:
        function_name = signature.group("name")

        if function_name.lower() == "main":
            continue

        open_brace = code.find(
            "{",
            signature.start(),
        )
        body, _ = _extract_braced_block(
            code,
            open_brace,
        )

        if not body:
            continue

        self_call_pattern = re.compile(
            rf"\b{re.escape(function_name)}\s*\((?P<args>[^()]*)\)",
            flags=re.IGNORECASE,
        )

        self_calls = list(
            self_call_pattern.finditer(body)
        )

        if not self_calls:
            continue

        result = _empty_recursive_result()
        result["function_name"] = function_name
        result["recursive_call_detected"] = True

        parameter_names = _extract_c_parameter_names(
            signature.group("params")
        )
        primary_param = (
            parameter_names[0]
            if parameter_names
            else None
        )

        result["base_case_detected"] = _has_c_base_case(
            body=body,
            primary_param=primary_param,
        )

        if primary_param is None:
            result["unknown_progress"] = True
            return result

        progress_found = False

        for call in self_calls:
            first_arg = _first_call_arg(
                call.group("args")
            )

            progress = _classify_c_recursive_argument(
                first_arg=first_arg,
                primary_param=primary_param,
            )

            if progress == "same_argument":
                result["same_argument"] = True
                progress_found = True
            elif progress == "increasing_argument":
                result["increasing_argument"] = True
                progress_found = True
            elif progress == "decreasing_argument":
                result["decreasing_argument"] = True
                progress_found = True
            else:
                result["unknown_progress"] = True

        if not progress_found and not result["unknown_progress"]:
            result["unknown_progress"] = True

        return result

    # C/C++ syntax exists, but no recursive function was found.
    return _empty_recursive_result()


def _extract_c_parameter_names(
    raw_params: str,
) -> list[str]:
    names: list[str] = []

    for raw_param in raw_params.split(","):
        parameter = raw_param.strip()

        if not parameter or parameter == "void":
            continue

        identifiers = re.findall(
            r"[A-Za-z_]\w*",
            parameter,
        )

        if identifiers:
            names.append(
                identifiers[-1]
            )

    return names


def _has_c_base_case(
    *,
    body: str,
    primary_param: str | None,
) -> bool:
    """
    Detect a C/C++ recursion stopping branch that returns without another
    recursive call from that branch.
    """

    if primary_param is None:
        return bool(
            re.search(
                r"\bif\s*\([^)]*\)\s*\{?\s*return\b",
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )
        )

    param = re.escape(primary_param)

    patterns = [
        rf"\bif\s*\([^)]*\b{param}\b[^)]*(?:<=|<|==)\s*(?:0|1)[^)]*\)"
        rf"\s*(?:\{{[^{{}}]*?\breturn\b|\breturn\b)",
        rf"\bif\s*\(\s*(?:0|1)\s*(?:>=|>|==)\s*\b{param}\b[^)]*\)"
        rf"\s*(?:\{{[^{{}}]*?\breturn\b|\breturn\b)",
    ]

    return any(
        re.search(
            pattern,
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for pattern in patterns
    )


def _classify_c_recursive_argument(
    *,
    first_arg: str | None,
    primary_param: str,
) -> str:
    if not first_arg:
        return "unknown"

    compact_arg = re.sub(
        r"\s+",
        "",
        first_arg,
    )

    param = re.escape(primary_param)

    if re.fullmatch(
        param,
        compact_arg,
    ):
        return "same_argument"

    if re.fullmatch(
        rf"{param}-\d+(?:\.\d+)?",
        compact_arg,
    ):
        return "decreasing_argument"

    if re.fullmatch(
        rf"{param}\+\d+(?:\.\d+)?",
        compact_arg,
    ):
        return "increasing_argument"

    return "unknown"

def _empty_recursive_result() -> dict[str, Any]:
    return {
        "function_name": None,
        "recursive_call_detected": False,
        "base_case_detected": False,
        "same_argument": False,
        "increasing_argument": False,
        "decreasing_argument": False,
        "unknown_progress": False,
    }


def _first_python_param(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
    positional_args = [
        *function_node.args.posonlyargs,
        *function_node.args.args,
    ]

    for argument in positional_args:
        if argument.arg not in {"self", "cls"}:
            return argument.arg

    return None


def _classify_python_recursive_argument(
    argument: ast.AST,
    primary_param: str,
) -> str:
    if isinstance(argument, ast.Name) and argument.id == primary_param:
        return "same_argument"

    if isinstance(argument, ast.BinOp):
        if (
            isinstance(argument.left, ast.Name)
            and argument.left.id == primary_param
            and _is_positive_numeric_constant(argument.right)
        ):
            if isinstance(argument.op, ast.Sub):
                return "decreasing_argument"

            if isinstance(argument.op, ast.Add):
                return "increasing_argument"

    return "unknown"


def _is_positive_numeric_constant(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
        and node.value > 0
    )


def _has_python_base_case(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    primary_param: str | None,
) -> bool:
    """
    Detect a plausible recursion stopping condition.

    A base case must:
    - be an if-condition,
    - test the primary recursion parameter when one exists, and
    - contain a return in that branch.
    """

    for node in ast.walk(function_node):
        if not isinstance(node, ast.If):
            continue

        if not any(
            isinstance(child, ast.Return)
            for statement in node.body
            for child in ast.walk(statement)
        ):
            continue

        if primary_param is None:
            return True

        if _condition_mentions_name(node.test, primary_param):
            return True

    return False


def _condition_mentions_name(condition: ast.AST, name: str) -> bool:
    return any(
        isinstance(node, ast.Name) and node.id == name
        for node in ast.walk(condition)
    )


def _extract_recursive_info_fallback(source_code: str) -> dict[str, Any]:
    """
    Conservative fallback for syntactically incomplete Python submissions.

    It only scans the indented body of the first detected function, preventing
    top-level test calls from being classified as recursion.
    """

    result = _empty_recursive_result()

    lines = source_code.splitlines()
    definition_index: int | None = None
    function_name: str | None = None
    primary_param: str | None = None
    definition_indent = 0

    definition_pattern = re.compile(
        r"^(?P<indent>\s*)def\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
        r"\((?P<params>[^)]*)\)\s*:"
    )

    for index, line in enumerate(lines):
        match = definition_pattern.match(line)
        if not match:
            continue

        definition_index = index
        function_name = match.group("name")
        params = _extract_params(match.group("params"))
        primary_param = params[0] if params else None
        definition_indent = len(match.group("indent").expandtabs(4))
        break

    if definition_index is None or function_name is None:
        return result

    body_lines: list[str] = []

    for line in lines[definition_index + 1 :]:
        if not line.strip():
            body_lines.append(line)
            continue

        current_indent = len(line) - len(line.lstrip(" \t"))
        if current_indent <= definition_indent:
            break

        body_lines.append(line)

    body = "\n".join(body_lines)
    result["function_name"] = function_name

    if not body.strip():
        return result

    call_pattern = re.compile(
        rf"\b{re.escape(function_name)}\s*\(([^)]*)\)"
    )
    calls = [match.group(1).strip() for match in call_pattern.finditer(body)]

    if not calls:
        return result

    result["recursive_call_detected"] = True
    result["base_case_detected"] = _has_base_case(body, primary_param)

    if primary_param is None:
        result["unknown_progress"] = True
        return result

    progress_found = False

    for call_args in calls:
        first_arg = _first_call_arg(call_args)

        if not first_arg:
            result["unknown_progress"] = True
            continue

        compact_arg = re.sub(r"\s+", "", first_arg)
        compact_param = re.escape(primary_param)

        if re.fullmatch(compact_param, compact_arg):
            result["same_argument"] = True
            progress_found = True
        elif re.fullmatch(rf"{compact_param}\+\d+(?:\.\d+)?", compact_arg):
            result["increasing_argument"] = True
            progress_found = True
        elif re.fullmatch(rf"{compact_param}-\d+(?:\.\d+)?", compact_arg):
            result["decreasing_argument"] = True
            progress_found = True
        else:
            result["unknown_progress"] = True

    if not progress_found and not result["unknown_progress"]:
        result["unknown_progress"] = True

    return result


def _extract_params(raw_params: str) -> list[str]:
    params: list[str] = []

    for raw_param in raw_params.split(","):
        param = raw_param.strip()

        if not param:
            continue

        param = param.split("=")[0].strip()
        param = param.split(":")[0].strip()

        if param in {"self", "cls"}:
            continue

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", param):
            params.append(param)

    return params


def _first_call_arg(raw_args: str) -> str | None:
    if not raw_args.strip():
        return None

    return raw_args.split(",")[0].strip()


def _has_base_case(code: str, primary_param: str | None) -> bool:
    normalized = code.lower()

    if "if" not in normalized or "return" not in normalized:
        return False

    if primary_param is None:
        return bool(
            re.search(
                r"\bif\b[^\n:]*:\s*(?:\n\s*)?return\b",
                normalized,
            )
        )

    param = re.escape(primary_param)

    param_condition_patterns = [
        rf"\bif\s+{param}\s*==\s*0\b",
        rf"\bif\s+{param}\s*==\s*1\b",
        rf"\bif\s+{param}\s*<=\s*0\b",
        rf"\bif\s+{param}\s*<=\s*1\b",
        rf"\bif\s+{param}\s*<\s*1\b",
        rf"\bif\s+{param}\s*>=\s*\d+\b",
    ]

    return any(
        re.search(pattern, normalized)
        for pattern in param_condition_patterns
    )


def _is_weak_submission(
    *,
    final_answer: str,
    written_reasoning: str,
    source_code: str,
    speech_transcript: str,
) -> bool:
    combined_text = " ".join(
        value
        for value in [
            final_answer,
            written_reasoning,
            speech_transcript,
        ]
        if value
    ).strip()

    has_enough_text = len(combined_text) >= 20
    has_code = len(source_code.strip()) >= 20

    return not has_enough_text and not has_code