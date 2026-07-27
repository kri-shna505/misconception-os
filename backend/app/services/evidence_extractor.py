from __future__ import annotations

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

    recursive_call_detected: bool
    recursive_function_name: str | None
    base_case_detected: bool
    missing_base_case: bool

    recursive_call_same_argument: bool
    recursive_call_increasing_argument: bool
    recursive_call_decreasing_argument: bool
    recursive_call_unknown_progress: bool

    weak_submission: bool


def extract_evidence(attempt: Any, problem: Any) -> EvidenceSignals:
    """
    Extract observable evidence from a saved student attempt and its seeded problem.

    This service does not decide the final misconception.
    It only produces evidence/signals that rule detectors can use later.
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

    reasoning_mentions_binary_search = _mentions_binary_search(combined_reasoning)

    if reasoning_mentions_binary_search:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.WRITTEN_REASONING,
                strength=EvidenceStrength.STRONG,
                text="Student reasoning mentions binary search or O(log n) search.",
                metadata={"matched_area": "final_answer/written_reasoning/speech_transcript"},
            )
        )

    code_uses_binary_search = _code_uses_binary_search(source_code)

    if code_uses_binary_search:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text="Student code uses a binary-search pattern with left/right/mid style logic.",
                metadata={"pattern": "binary_search"},
            )
        )

    recursive_info = _extract_recursive_info(source_code)

    if recursive_info["recursive_call_detected"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text=f"Recursive self-call detected in function '{recursive_info['function_name']}'.",
                metadata={"function_name": recursive_info["function_name"]},
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
                text="Recursive call is present, but no clear base-case condition was detected.",
                metadata={"missing_base_case": True},
            )
        )

    if recursive_info["same_argument"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text="Recursive call appears to reuse the same argument without reducing the problem size.",
                metadata={"progress": "same_argument"},
            )
        )

    if recursive_info["increasing_argument"]:
        evidence.append(
            RuleEvidence(
                source=EvidenceSource.SOURCE_CODE,
                strength=EvidenceStrength.STRONG,
                text="Recursive call appears to increase the argument instead of reducing it.",
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
                text="Recursive call was detected, but argument progress is unclear.",
                metadata={"progress": "unknown"},
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
                text="Submission contains limited evidence for reliable misconception diagnosis.",
                metadata={"weak_submission": True},
            )
        )

    return EvidenceSignals(
        evidence=evidence,
        problem_array=problem_array,
        problem_array_is_unsorted=problem_array_is_unsorted,
        reasoning_mentions_binary_search=reasoning_mentions_binary_search,
        code_uses_binary_search=code_uses_binary_search,
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

        if isinstance(item, int | float):
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

    return any(values[index] > values[index + 1] for index in range(len(values) - 1))


def _mentions_binary_search(text: str) -> bool:
    normalized = text.lower()

    binary_search_patterns = [
        "binary search",
        "binary-search",
        "o(log n)",
        "ologn",
        "log n",
        "divide and conquer search",
    ]

    return any(pattern in normalized for pattern in binary_search_patterns)


def _code_uses_binary_search(source_code: str) -> bool:
    code = source_code.lower()

    if not code:
        return False

    has_mid = bool(re.search(r"\bmid\b", code))
    has_left_right = (
        bool(re.search(r"\b(left|lo|low)\b", code))
        and bool(re.search(r"\b(right|hi|high)\b", code))
    )
    has_loop = "while" in code or "for" in code
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


def _extract_recursive_info(source_code: str) -> dict[str, Any]:
    code = source_code.strip()

    result: dict[str, Any] = {
        "function_name": None,
        "recursive_call_detected": False,
        "base_case_detected": False,
        "same_argument": False,
        "increasing_argument": False,
        "decreasing_argument": False,
        "unknown_progress": False,
    }

    if not code:
        return result

    function_match = re.search(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", code)

    if not function_match:
        return result

    function_name = function_match.group(1)
    params = _extract_params(function_match.group(2))
    primary_param = params[0] if params else None

    result["function_name"] = function_name

    call_pattern = re.compile(
        rf"\b{re.escape(function_name)}\s*\(([^)]*)\)",
        flags=re.MULTILINE,
    )

    calls = [
        call.group(1).strip()
        for call in call_pattern.finditer(code)
        if call.start() > function_match.end()
    ]

    if not calls:
        return result

    result["recursive_call_detected"] = True
    result["base_case_detected"] = _has_base_case(code, primary_param)

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
            continue

        if re.fullmatch(rf"{compact_param}\+\d+", compact_arg):
            result["increasing_argument"] = True
            progress_found = True
            continue

        if re.fullmatch(rf"{compact_param}-\d+", compact_arg):
            result["decreasing_argument"] = True
            progress_found = True
            continue

        if re.fullmatch(rf"{compact_param}\s*-\s*\d+", first_arg):
            result["decreasing_argument"] = True
            progress_found = True
            continue

        if re.fullmatch(rf"{compact_param}\s*\+\s*\d+", first_arg):
            result["increasing_argument"] = True
            progress_found = True
            continue

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

    generic_base_patterns = [
        r"\bif\b.+\breturn\b",
        r"\bif\b.+:\s*\n\s*return\b",
    ]

    if not any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in generic_base_patterns):
        return False

    if primary_param is None:
        return True

    param = re.escape(primary_param)

    param_condition_patterns = [
        rf"\bif\s+{param}\s*==\s*0\b",
        rf"\bif\s+{param}\s*==\s*1\b",
        rf"\bif\s+{param}\s*<=\s*0\b",
        rf"\bif\s+{param}\s*<=\s*1\b",
        rf"\bif\s+{param}\s*<\s*1\b",
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
        value for value in [final_answer, written_reasoning, speech_transcript] if value
    ).strip()

    has_enough_text = len(combined_text) >= 20
    has_code = len(source_code.strip()) >= 20

    return not has_enough_text and not has_code