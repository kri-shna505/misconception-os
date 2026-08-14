from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final


FEATURE_VERSION: Final[str] = "features-v1.0"


@dataclass(frozen=True, slots=True)
class MLFeatureRecord:
    """
    Canonical runtime/offline feature representation for one attempt.

    This object deliberately keeps raw text/code fields separate from
    numeric metadata so later training stages can choose their own
    vectorization strategy.

    Sprint 11 principle:

    - written reasoning and speech provide semantic evidence;
    - source code provides implementation evidence;
    - rule outputs are optional supporting features;
    - teacher-review labels are NOT stored here because labels must
      remain separate from model inputs.
    """

    attempt_id: str
    problem_id: str

    reasoning_text: str
    source_code: str
    speech_text: str

    combined_text: str

    selected_language: str
    input_language: str
    input_modality: str

    response_time_seconds: float

    has_reasoning: int
    has_code: int
    has_speech: int

    reasoning_length: int
    source_code_length: int
    speech_length: int
    combined_text_length: int

    rule_confidence: float
    rule_score: float

    rule_state: str
    rule_misconception_id: str

    feature_version: str = FEATURE_VERSION

    def to_dict(self) -> dict[str, Any]:
        """
        Return a serialization-safe dictionary.
        """

        return asdict(self)


def normalize_text(
    value: Any,
) -> str:
    """
    Normalize optional text-like input.

    The function intentionally performs conservative normalization:

    - None becomes an empty string;
    - surrounding whitespace is removed;
    - internal whitespace is preserved.

    We do not lowercase text here because multilingual input,
    source-code identifiers, acronyms, and code-switched content may
    depend on case.
    """

    if value is None:
        return ""

    return str(value).strip()


def normalize_category(
    value: Any,
    *,
    fallback: str = "unknown",
) -> str:
    """
    Normalize a categorical feature.

    Categories are lowercased because values such as Python/python or
    Telugu/telugu should map to one stable representation.
    """

    normalized = normalize_text(
        value
    )

    if not normalized:
        return fallback

    return normalized.lower()


def normalize_probability(
    value: Any,
) -> float:
    """
    Convert an optional probability-like value into a safe float.

    Missing values become 0.0.

    Existing diagnosis score fields are expected to be in [0, 1].
    Values outside that range are clamped defensively so malformed
    historical records cannot crash feature construction.
    """

    if value is None:
        return 0.0

    try:
        numeric_value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    if numeric_value < 0.0:
        return 0.0

    if numeric_value > 1.0:
        return 1.0

    return numeric_value


def normalize_duration(
    value: Any,
) -> float:
    """
    Normalize response duration.

    Missing, malformed, or negative values become 0.0.
    """

    if value is None:
        return 0.0

    try:
        numeric_value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    if numeric_value < 0.0:
        return 0.0

    return numeric_value


def build_combined_text(
    *,
    reasoning_text: str,
    speech_text: str,
) -> str:
    """
    Build the semantic text consumed by baseline NLP models.

    Written reasoning remains first because it is the student's primary
    explicit explanation.

    Speech text is appended when present.

    Source code is intentionally excluded from this string. Code should
    remain a separate feature channel rather than being blindly mixed
    into natural-language TF-IDF text.
    """

    components: list[str] = []

    if reasoning_text:
        components.append(
            reasoning_text
        )

    if speech_text:
        components.append(
            speech_text
        )

    return "\n".join(
        components
    )


def infer_modality_flags(
    *,
    reasoning_text: str,
    source_code: str,
    speech_text: str,
) -> tuple[int, int, int]:
    """
    Return binary feature-presence flags.

    Returns:

        (
            has_reasoning,
            has_code,
            has_speech,
        )
    """

    return (
        int(bool(reasoning_text)),
        int(bool(source_code)),
        int(bool(speech_text)),
    )


def build_feature_record(
    *,
    attempt_id: Any,
    problem_id: Any,
    written_reasoning: Any = None,
    normalized_reasoning: Any = None,
    source_code: Any = None,
    speech_transcript: Any = None,
    selected_language: Any = None,
    input_language: Any = None,
    input_modality: Any = None,
    response_time_seconds: Any = None,
    rule_state: Any = None,
    rule_misconception_id: Any = None,
    rule_confidence: Any = None,
    rule_score: Any = None,
) -> MLFeatureRecord:
    """
    Build one canonical ML feature record.

    ``normalized_reasoning`` is preferred when available because the
    Sprint 10 processing layer may already have produced a normalized
    representation.

    Raw ``written_reasoning`` remains the fallback.
    """

    normalized_reasoning_text = normalize_text(
        normalized_reasoning
    )

    raw_reasoning_text = normalize_text(
        written_reasoning
    )

    reasoning_text = (
        normalized_reasoning_text
        or raw_reasoning_text
    )

    normalized_source_code = normalize_text(
        source_code
    )

    normalized_speech_text = normalize_text(
        speech_transcript
    )

    combined_text = build_combined_text(
        reasoning_text=reasoning_text,
        speech_text=normalized_speech_text,
    )

    (
        has_reasoning,
        has_code,
        has_speech,
    ) = infer_modality_flags(
        reasoning_text=reasoning_text,
        source_code=normalized_source_code,
        speech_text=normalized_speech_text,
    )

    return MLFeatureRecord(
        attempt_id=normalize_text(
            attempt_id
        ),
        problem_id=normalize_text(
            problem_id
        ),
        reasoning_text=reasoning_text,
        source_code=normalized_source_code,
        speech_text=normalized_speech_text,
        combined_text=combined_text,
        selected_language=normalize_category(
            selected_language
        ),
        input_language=normalize_category(
            input_language
        ),
        input_modality=normalize_category(
            input_modality
        ),
        response_time_seconds=normalize_duration(
            response_time_seconds
        ),
        has_reasoning=has_reasoning,
        has_code=has_code,
        has_speech=has_speech,
        reasoning_length=len(
            reasoning_text
        ),
        source_code_length=len(
            normalized_source_code
        ),
        speech_length=len(
            normalized_speech_text
        ),
        combined_text_length=len(
            combined_text
        ),
        rule_confidence=normalize_probability(
            rule_confidence
        ),
        rule_score=normalize_probability(
            rule_score
        ),
        rule_state=normalize_category(
            rule_state,
            fallback="missing",
        ),
        rule_misconception_id=normalize_text(
            rule_misconception_id
        ),
    )


def build_feature_record_from_mapping(
    row: dict[str, Any],
) -> MLFeatureRecord:
    """
    Build features from one exported dataset row.

    This keeps offline training compatible with the same feature
    contract used by runtime inference.
    """

    return build_feature_record(
        attempt_id=row.get(
            "attempt_id"
        ),
        problem_id=row.get(
            "problem_id"
        ),
        written_reasoning=row.get(
            "written_reasoning"
        ),
        normalized_reasoning=row.get(
            "normalized_reasoning"
        ),
        source_code=row.get(
            "source_code"
        ),
        speech_transcript=row.get(
            "speech_transcript"
        ),
        selected_language=row.get(
            "selected_language"
        ),
        input_language=row.get(
            "input_language"
        ),
        input_modality=row.get(
            "input_modality"
        ),
        response_time_seconds=row.get(
            "response_time_seconds"
        ),
        rule_state=row.get(
            "rule_state"
        ),
        rule_misconception_id=row.get(
            "rule_misconception_id"
        ),
        rule_confidence=row.get(
            "rule_confidence"
        ),
        rule_score=row.get(
            "rule_score"
        ),
    )


def get_numeric_feature_dict(
    features: MLFeatureRecord,
) -> dict[str, float]:
    """
    Return only numeric features suitable for baseline estimators.

    Text vectorization is handled separately by the training pipeline.
    """

    return {
        "response_time_seconds": (
            features.response_time_seconds
        ),
        "has_reasoning": float(
            features.has_reasoning
        ),
        "has_code": float(
            features.has_code
        ),
        "has_speech": float(
            features.has_speech
        ),
        "reasoning_length": float(
            features.reasoning_length
        ),
        "source_code_length": float(
            features.source_code_length
        ),
        "speech_length": float(
            features.speech_length
        ),
        "combined_text_length": float(
            features.combined_text_length
        ),
        "rule_confidence": (
            features.rule_confidence
        ),
        "rule_score": (
            features.rule_score
        ),
    }


__all__ = [
    "FEATURE_VERSION",
    "MLFeatureRecord",
    "build_combined_text",
    "build_feature_record",
    "build_feature_record_from_mapping",
    "get_numeric_feature_dict",
    "infer_modality_flags",
    "normalize_category",
    "normalize_duration",
    "normalize_probability",
    "normalize_text",
]