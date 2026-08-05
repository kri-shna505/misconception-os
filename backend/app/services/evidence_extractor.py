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

    stack_heap_confusion_detected: bool
    single_stack_frame_claim_detected: bool
    locals_survive_return_claim_detected: bool
    recursive_locals_on_heap_claim_detected: bool


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
        parameter_reassignment_claims_caller_mutation=_contains_any(
            combined_reasoning,
            [
                "changing the local parameters changes the caller variables",
                "local reassignment modifies the caller",
            ],
        ),
        pass_by_value_confusion_detected=_contains_any(
            combined_reasoning,
            [
                "pass by value changes the original variable",
                "parameters are references by default",
            ],
        ),
        swap_uses_only_local_reassignment=_contains_any(
            source_code,
            [
                "temp = a",
                "a = b",
                "b = temp",
            ],
        ),
        pointer_based_swap_detected=_contains_any(
            source_code,
            [
                "*a",
                "*b",
                "&",
            ],
        ),
        return_based_swap_detected=_contains_any(
            source_code,
            [
                "return",
            ],
        ),

        stack_heap_confusion_detected=_contains_any(
            combined_reasoning,
            [
                "stack and heap are the same",
                "function call frames are stored on the heap",
            ],
        ),
        single_stack_frame_claim_detected=_contains_any(
            combined_reasoning,
            [
                "only one stack frame",
                "recursive calls reuse one stack frame",
            ],
        ),
        locals_survive_return_claim_detected=_contains_any(
            combined_reasoning,
            [
                "local variables remain after the function returns",
                "stack variables survive after return",
            ],
        ),
        recursive_locals_on_heap_claim_detected=_contains_any(
            combined_reasoning,
            [
                "all recursive local variables are stored on the heap",
            ],
        ),
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

    Strong linear-search evidence requires:
    - iteration over a collection or its enumerate/range(len(...)) form,
    - comparison of the current element with a target-like value, and
    - a return from the matching branch.

    The detector is intentionally conservative so ordinary loops are not
    mislabeled as linear search.
    """

    code = source_code.strip()
    if not code:
        return False

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
    ]

    return any(
        re.search(pattern, normalized, flags=re.DOTALL)
        for pattern in patterns
    )

def _extract_recursive_info(source_code: str) -> dict[str, Any]:
    """
    Extract recursion signals from Python source code.

    The previous regex implementation scanned the whole file and therefore
    mistook a normal top-level call such as:

        result = search_target(arr, target)

    for a recursive call. This implementation parses the Python AST and only
    counts self-calls that occur inside the corresponding function body.
    """

    result = _empty_recursive_result()

    code = source_code.strip()
    if not code:
        return result

    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Keep a conservative fallback for incomplete student code. The fallback
        # isolates the function body by indentation before looking for self-calls.
        return _extract_recursive_info_fallback(code)

    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    if not functions:
        return result

    # Prefer the first top-level function because seeded attempts normally
    # contain one primary solution function.
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