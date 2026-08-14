from __future__ import annotations

import uuid

import pytest

from app.ml.feature_builder import (
    FEATURE_VERSION,
    MLFeatureRecord,
    build_combined_text,
    build_feature_record,
    build_feature_record_from_mapping,
    get_numeric_feature_dict,
    infer_modality_flags,
    normalize_category,
    normalize_duration,
    normalize_probability,
    normalize_text,
)


def test_normalize_text_returns_empty_string_for_none() -> None:
    assert normalize_text(None) == ""


def test_normalize_text_trims_outer_whitespace() -> None:
    assert normalize_text("  hello world  ") == "hello world"


def test_normalize_text_preserves_internal_whitespace() -> None:
    assert normalize_text("hello   world") == "hello   world"


def test_normalize_text_preserves_case() -> None:
    assert normalize_text("Binary Search") == "Binary Search"


def test_normalize_category_lowercases_and_trims() -> None:
    assert normalize_category(" Python ") == "python"
    assert normalize_category("TELUGU") == "telugu"


def test_normalize_category_uses_unknown_fallback() -> None:
    assert normalize_category(None) == "unknown"
    assert normalize_category("") == "unknown"
    assert normalize_category("   ") == "unknown"


def test_normalize_category_supports_custom_fallback() -> None:
    assert (
        normalize_category(
            None,
            fallback="missing",
        )
        == "missing"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 0.0),
        ("", 0.0),
        ("invalid", 0.0),
        (-1, 0.0),
        (-0.25, 0.0),
        (0, 0.0),
        (0.25, 0.25),
        ("0.5", 0.5),
        (1, 1.0),
        (2, 1.0),
    ],
)
def test_normalize_probability(
    value: object,
    expected: float,
) -> None:
    assert normalize_probability(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 0.0),
        ("", 0.0),
        ("invalid", 0.0),
        (-10, 0.0),
        (0, 0.0),
        (2.5, 2.5),
        ("14", 14.0),
        ("18.75", 18.75),
    ],
)
def test_normalize_duration(
    value: object,
    expected: float,
) -> None:
    assert normalize_duration(value) == expected


def test_build_combined_text_with_reasoning_only() -> None:
    combined = build_combined_text(
        reasoning_text="Use linear search.",
        speech_text="",
    )

    assert combined == "Use linear search."


def test_build_combined_text_with_speech_only() -> None:
    combined = build_combined_text(
        reasoning_text="",
        speech_text="The array is not sorted.",
    )

    assert combined == "The array is not sorted."


def test_build_combined_text_with_reasoning_and_speech() -> None:
    combined = build_combined_text(
        reasoning_text="I will scan the array.",
        speech_text="Binary search requires sorted input.",
    )

    assert combined == (
        "I will scan the array.\n"
        "Binary search requires sorted input."
    )


def test_build_combined_text_with_no_text_returns_empty_string() -> None:
    combined = build_combined_text(
        reasoning_text="",
        speech_text="",
    )

    assert combined == ""


@pytest.mark.parametrize(
    (
        "reasoning_text",
        "source_code",
        "speech_text",
        "expected",
    ),
    [
        (
            "",
            "",
            "",
            (0, 0, 0),
        ),
        (
            "reasoning",
            "",
            "",
            (1, 0, 0),
        ),
        (
            "",
            "code",
            "",
            (0, 1, 0),
        ),
        (
            "",
            "",
            "speech",
            (0, 0, 1),
        ),
        (
            "reasoning",
            "code",
            "speech",
            (1, 1, 1),
        ),
    ],
)
def test_infer_modality_flags(
    reasoning_text: str,
    source_code: str,
    speech_text: str,
    expected: tuple[int, int, int],
) -> None:
    assert (
        infer_modality_flags(
            reasoning_text=reasoning_text,
            source_code=source_code,
            speech_text=speech_text,
        )
        == expected
    )


def test_feature_builder_prefers_normalized_reasoning() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning="RAW reasoning",
        normalized_reasoning="Normalized reasoning",
    )

    assert features.reasoning_text == "Normalized reasoning"


def test_feature_builder_falls_back_to_written_reasoning() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning="Use linear search.",
        normalized_reasoning=None,
    )

    assert features.reasoning_text == "Use linear search."


def test_feature_builder_falls_back_when_normalized_reasoning_blank() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning="Use linear search.",
        normalized_reasoning="   ",
    )

    assert features.reasoning_text == "Use linear search."


def test_feature_builder_preserves_code_separately_from_combined_text() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning="I will scan each item.",
        source_code="for value in arr:\n    pass",
        speech_transcript="The array is unsorted.",
    )

    assert "for value in arr" in features.source_code

    assert "for value in arr" not in features.combined_text

    assert features.combined_text == (
        "I will scan each item.\n"
        "The array is unsorted."
    )


def test_feature_builder_preserves_telugu_and_code_switch_text() -> None:
    text = (
        "ఈ array sorted కాదు. "
        "So linear search use చేస్తాను."
    )

    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning=text,
        input_language="Telugu",
    )

    assert features.reasoning_text == text
    assert features.combined_text == text
    assert features.input_language == "telugu"


def test_feature_builder_builds_text_code_speech_flags() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning="Binary search should work.",
        source_code="while left <= right:\n    pass",
        speech_transcript="I will use the middle value.",
    )

    assert features.has_reasoning == 1
    assert features.has_code == 1
    assert features.has_speech == 1


def test_feature_builder_builds_text_only_flags() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning="Use linear search.",
        source_code=None,
        speech_transcript=None,
    )

    assert features.has_reasoning == 1
    assert features.has_code == 0
    assert features.has_speech == 0


def test_feature_builder_normalizes_categories() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        selected_language=" Python ",
        input_language=" Telugu ",
        input_modality=" Text + Code + Speech ",
        rule_state=" CONFIDENT ",
    )

    assert features.selected_language == "python"
    assert features.input_language == "telugu"
    assert features.input_modality == "text + code + speech"
    assert features.rule_state == "confident"


def test_feature_builder_uses_missing_for_missing_rule_state() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        rule_state=None,
    )

    assert features.rule_state == "missing"


def test_feature_builder_clamps_rule_scores() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        rule_confidence=1.5,
        rule_score=-1,
    )

    assert features.rule_confidence == 1.0
    assert features.rule_score == 0.0


def test_feature_builder_normalizes_duration() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        response_time_seconds="42.5",
    )

    assert features.response_time_seconds == 42.5


def test_feature_builder_rejects_negative_duration_by_normalizing_to_zero() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        response_time_seconds=-15,
    )

    assert features.response_time_seconds == 0.0


def test_feature_builder_calculates_lengths() -> None:
    reasoning = "abc"
    code = "12345"
    speech = "abcdef"

    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
        written_reasoning=reasoning,
        source_code=code,
        speech_transcript=speech,
    )

    combined = f"{reasoning}\n{speech}"

    assert features.reasoning_length == len(reasoning)
    assert features.source_code_length == len(code)
    assert features.speech_length == len(speech)
    assert features.combined_text_length == len(combined)


def test_feature_builder_sets_feature_version() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
    )

    assert features.feature_version == FEATURE_VERSION
    assert FEATURE_VERSION == "features-v1.0"


def test_feature_builder_returns_ml_feature_record() -> None:
    features = build_feature_record(
        attempt_id=uuid.uuid4(),
        problem_id=uuid.uuid4(),
    )

    assert isinstance(features, MLFeatureRecord)


def test_feature_record_to_dict_returns_expected_fields() -> None:
    attempt_id = uuid.uuid4()
    problem_id = uuid.uuid4()

    features = build_feature_record(
        attempt_id=attempt_id,
        problem_id=problem_id,
        written_reasoning="reasoning",
        source_code="code",
        speech_transcript="speech",
        selected_language="Python",
        input_language="English",
        input_modality="Text + Code + Speech",
        response_time_seconds=11,
        rule_state="possible",
        rule_misconception_id="M1",
        rule_confidence=0.68,
        rule_score=0.7,
    )

    payload = features.to_dict()

    assert payload["attempt_id"] == str(attempt_id)
    assert payload["problem_id"] == str(problem_id)
    assert payload["reasoning_text"] == "reasoning"
    assert payload["source_code"] == "code"
    assert payload["speech_text"] == "speech"
    assert payload["selected_language"] == "python"
    assert payload["input_language"] == "english"
    assert payload["rule_confidence"] == 0.68
    assert payload["feature_version"] == FEATURE_VERSION


def test_build_feature_record_from_mapping() -> None:
    attempt_id = str(uuid.uuid4())
    problem_id = str(uuid.uuid4())

    row = {
        "attempt_id": attempt_id,
        "problem_id": problem_id,
        "written_reasoning": "raw",
        "normalized_reasoning": "normalized",
        "source_code": "print('hello')",
        "speech_transcript": "speech text",
        "selected_language": "Python",
        "input_language": "Telugu",
        "input_modality": "Text + Code + Speech",
        "response_time_seconds": "20",
        "rule_state": "confident",
        "rule_misconception_id": "M1",
        "rule_confidence": "0.92",
        "rule_score": "0.9",
    }

    features = build_feature_record_from_mapping(row)

    assert features.attempt_id == attempt_id
    assert features.problem_id == problem_id
    assert features.reasoning_text == "normalized"
    assert features.source_code == "print('hello')"
    assert features.speech_text == "speech text"
    assert features.input_language == "telugu"
    assert features.has_reasoning == 1
    assert features.has_code == 1
    assert features.has_speech == 1
    assert features.rule_confidence == 0.92
    assert features.rule_score == 0.9


def test_build_feature_record_from_mapping_handles_missing_fields() -> None:
    features = build_feature_record_from_mapping(
        {
            "attempt_id": "attempt-1",
            "problem_id": "problem-1",
        }
    )

    assert features.attempt_id == "attempt-1"
    assert features.problem_id == "problem-1"

    assert features.reasoning_text == ""
    assert features.source_code == ""
    assert features.speech_text == ""

    assert features.selected_language == "unknown"
    assert features.input_language == "unknown"
    assert features.input_modality == "unknown"

    assert features.rule_state == "missing"

    assert features.has_reasoning == 0
    assert features.has_code == 0
    assert features.has_speech == 0


def test_numeric_feature_dict_contains_only_numeric_features() -> None:
    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
        written_reasoning="abc",
        source_code="code",
        speech_transcript="speech",
        response_time_seconds=12,
        rule_confidence=0.92,
        rule_score=0.85,
    )

    numeric = get_numeric_feature_dict(
        features
    )

    assert numeric == {
        "response_time_seconds": 12.0,
        "has_reasoning": 1.0,
        "has_code": 1.0,
        "has_speech": 1.0,
        "reasoning_length": 3.0,
        "source_code_length": 4.0,
        "speech_length": 6.0,
        "combined_text_length": float(
            len("abc\nspeech")
        ),
        "rule_confidence": 0.92,
        "rule_score": 0.85,
    }


def test_numeric_feature_dict_values_are_numeric() -> None:
    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
        written_reasoning="reasoning",
    )

    numeric = get_numeric_feature_dict(
        features
    )

    assert numeric

    assert all(
        isinstance(value, float)
        for value in numeric.values()
    )


def test_teacher_label_fields_are_not_part_of_feature_contract() -> None:
    """
    Critical anti-leakage test.

    Supervised teacher-review outcomes must never appear inside
    MLFeatureRecord because those fields are training targets, not model
    inputs.
    """

    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
        written_reasoning="reasoning",
    )

    payload = features.to_dict()

    assert "target_state" not in payload
    assert "target_misconception_id" not in payload
    assert "teacher_decision" not in payload
    assert "teacher_review_id" not in payload


def test_feature_builder_does_not_require_rule_output() -> None:
    """
    Runtime ML inference must still be able to construct features when a
    rule prediction is unavailable.
    """

    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
        written_reasoning="reasoning",
        rule_state=None,
        rule_misconception_id=None,
        rule_confidence=None,
        rule_score=None,
    )

    assert features.rule_state == "missing"
    assert features.rule_misconception_id == ""
    assert features.rule_confidence == 0.0
    assert features.rule_score == 0.0


def test_feature_builder_handles_speech_only_attempt() -> None:
    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
        written_reasoning=None,
        source_code=None,
        speech_transcript=(
            "Binary search requires sorted input."
        ),
        input_modality="speech",
    )

    assert features.reasoning_text == ""
    assert (
        features.speech_text
        == "Binary search requires sorted input."
    )

    assert (
        features.combined_text
        == "Binary search requires sorted input."
    )

    assert features.has_reasoning == 0
    assert features.has_code == 0
    assert features.has_speech == 1


def test_feature_builder_handles_code_only_attempt() -> None:
    code = (
        "for index, value in enumerate(arr):\n"
        "    if value == target:\n"
        "        return index"
    )

    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
        written_reasoning=None,
        source_code=code,
        speech_transcript=None,
        input_modality="code",
    )

    assert features.source_code == code
    assert features.combined_text == ""

    assert features.has_reasoning == 0
    assert features.has_code == 1
    assert features.has_speech == 0


def test_feature_builder_handles_empty_attempt_without_crashing() -> None:
    features = build_feature_record(
        attempt_id="attempt-1",
        problem_id="problem-1",
    )

    assert features.reasoning_text == ""
    assert features.source_code == ""
    assert features.speech_text == ""
    assert features.combined_text == ""

    assert features.reasoning_length == 0
    assert features.source_code_length == 0
    assert features.speech_length == 0
    assert features.combined_text_length == 0