from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.fusion import (
    FusionConfig,
    RulePrediction,
)
from app.services.ml_diagnosis_service import (
    ML_DIAGNOSIS_SERVICE_VERSION,
    MLDiagnosisServiceResult,
    build_attempt_ml_payload,
    diagnose_with_ml,
    diagnose_with_ml_from_mapping,
    diagnosis_model_fields,
    ml_diagnosis_available,
    rule_only_diagnosis_model_fields,
)


TEXT_COLUMN = "combined_text"

NUMERIC_COLUMNS = [
    "response_time_seconds",
    "has_reasoning",
    "has_code",
    "has_speech",
    "reasoning_length",
    "source_code_length",
    "speech_length",
    "combined_text_length",
    "rule_confidence",
    "rule_score",
]

CATEGORICAL_COLUMNS = [
    "selected_language",
    "input_language",
    "input_modality",
    "rule_state",
    "rule_misconception_id",
]

MODEL_VERSION = "baseline-logreg-test-v1.0"


def _training_row(
    *,
    combined_text: str,
    response_time_seconds: float,
    has_reasoning: float,
    has_code: float,
    has_speech: float,
    reasoning_length: float,
    source_code_length: float,
    speech_length: float,
    rule_confidence: float,
    rule_score: float,
    selected_language: str,
    input_language: str,
    input_modality: str,
    rule_state: str,
    rule_misconception_id: str,
    target_state: str,
) -> dict[str, Any]:
    return {
        "combined_text": combined_text,
        "response_time_seconds": response_time_seconds,
        "has_reasoning": has_reasoning,
        "has_code": has_code,
        "has_speech": has_speech,
        "reasoning_length": reasoning_length,
        "source_code_length": source_code_length,
        "speech_length": speech_length,
        "combined_text_length": float(
            len(combined_text)
        ),
        "rule_confidence": rule_confidence,
        "rule_score": rule_score,
        "selected_language": selected_language,
        "input_language": input_language,
        "input_modality": input_modality,
        "rule_state": rule_state,
        "rule_misconception_id": rule_misconception_id,
        "target_state": target_state,
    }


def _build_training_frame() -> pd.DataFrame:
    rows = [
        _training_row(
            combined_text=(
                "Binary search requires sorted input. "
                "I will use linear search."
            ),
            response_time_seconds=30,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=55,
            source_code_length=70,
            speech_length=0,
            rule_confidence=0.95,
            rule_score=0.95,
            selected_language="python",
            input_language="english",
            input_modality="text + code",
            rule_state="no_misconception",
            rule_misconception_id="missing",
            target_state="no_misconception",
        ),
        _training_row(
            combined_text=(
                "This array is unsorted, so scan each element."
            ),
            response_time_seconds=33,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=48,
            source_code_length=60,
            speech_length=0,
            rule_confidence=0.93,
            rule_score=0.92,
            selected_language="python",
            input_language="english",
            input_modality="text + code",
            rule_state="no_misconception",
            rule_misconception_id="missing",
            target_state="no_misconception",
        ),
        _training_row(
            combined_text=(
                "ఈ array sorted కాదు. "
                "Linear search use చేస్తాను."
            ),
            response_time_seconds=38,
            has_reasoning=1,
            has_code=1,
            has_speech=1,
            reasoning_length=45,
            source_code_length=55,
            speech_length=30,
            rule_confidence=0.94,
            rule_score=0.93,
            selected_language="python",
            input_language="telugu",
            input_modality="text + code + speech",
            rule_state="no_misconception",
            rule_misconception_id="missing",
            target_state="no_misconception",
        ),
        _training_row(
            combined_text=(
                "I will use binary search directly "
                "and discard half each time."
            ),
            response_time_seconds=45,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=65,
            source_code_length=100,
            speech_length=0,
            rule_confidence=0.92,
            rule_score=0.95,
            selected_language="python",
            input_language="english",
            input_modality="text + code",
            rule_state="confident",
            rule_misconception_id="M1",
            target_state="confident",
        ),
        _training_row(
            combined_text=(
                "Binary search works even without sorting."
            ),
            response_time_seconds=42,
            has_reasoning=1,
            has_code=1,
            has_speech=1,
            reasoning_length=44,
            source_code_length=85,
            speech_length=45,
            rule_confidence=0.94,
            rule_score=0.96,
            selected_language="python",
            input_language="english",
            input_modality="text + code + speech",
            rule_state="confident",
            rule_misconception_id="M1",
            target_state="confident",
        ),
        _training_row(
            combined_text=(
                "Array order check చేయాల్సిన అవసరం లేదు."
            ),
            response_time_seconds=43,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=42,
            source_code_length=80,
            speech_length=0,
            rule_confidence=0.91,
            rule_score=0.93,
            selected_language="python",
            input_language="telugu",
            input_modality="text + code",
            rule_state="confident",
            rule_misconception_id="M1",
            target_state="confident",
        ),
        _training_row(
            combined_text=(
                "I think binary search may work, "
                "but I am not sure about sorting."
            ),
            response_time_seconds=32,
            has_reasoning=1,
            has_code=0,
            has_speech=0,
            reasoning_length=70,
            source_code_length=0,
            speech_length=0,
            rule_confidence=0.62,
            rule_score=0.64,
            selected_language="python",
            input_language="english",
            input_modality="text",
            rule_state="possible",
            rule_misconception_id="M1",
            target_state="possible",
        ),
        _training_row(
            combined_text=(
                "Maybe compare with the middle element."
            ),
            response_time_seconds=28,
            has_reasoning=1,
            has_code=0,
            has_speech=1,
            reasoning_length=40,
            source_code_length=0,
            speech_length=35,
            rule_confidence=0.61,
            rule_score=0.63,
            selected_language="python",
            input_language="english",
            input_modality="text + speech",
            rule_state="possible",
            rule_misconception_id="M1",
            target_state="possible",
        ),
        _training_row(
            combined_text=(
                "Middle element compare చేస్తే "
                "half remove చేయొచ్చేమో."
            ),
            response_time_seconds=34,
            has_reasoning=1,
            has_code=0,
            has_speech=0,
            reasoning_length=48,
            source_code_length=0,
            speech_length=0,
            rule_confidence=0.60,
            rule_score=0.62,
            selected_language="python",
            input_language="telugu",
            input_modality="text",
            rule_state="possible",
            rule_misconception_id="M1",
            target_state="possible",
        ),
        _training_row(
            combined_text="I don't know.",
            response_time_seconds=9,
            has_reasoning=1,
            has_code=0,
            has_speech=0,
            reasoning_length=13,
            source_code_length=0,
            speech_length=0,
            rule_confidence=0.20,
            rule_score=0.15,
            selected_language="python",
            input_language="english",
            input_modality="text",
            rule_state="insufficient",
            rule_misconception_id="missing",
            target_state="insufficient",
        ),
        _training_row(
            combined_text="Not sure what algorithm to use.",
            response_time_seconds=11,
            has_reasoning=1,
            has_code=0,
            has_speech=0,
            reasoning_length=31,
            source_code_length=0,
            speech_length=0,
            rule_confidence=0.22,
            rule_score=0.17,
            selected_language="python",
            input_language="english",
            input_modality="text",
            rule_state="insufficient",
            rule_misconception_id="missing",
            target_state="insufficient",
        ),
        _training_row(
            combined_text="ఏ algorithm use చేయాలో తెలియదు.",
            response_time_seconds=10,
            has_reasoning=1,
            has_code=0,
            has_speech=0,
            reasoning_length=30,
            source_code_length=0,
            speech_length=0,
            rule_confidence=0.21,
            rule_score=0.16,
            selected_language="python",
            input_language="telugu",
            input_modality="text",
            rule_state="insufficient",
            rule_misconception_id="missing",
            target_state="insufficient",
        ),
    ]

    return pd.DataFrame(rows)


def _build_pipeline() -> Pipeline:
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                ),
                TEXT_COLUMN,
            ),
            (
                "numeric",
                Pipeline(
                    steps=[
                        (
                            "scale",
                            StandardScaler(),
                        ),
                    ]
                ),
                NUMERIC_COLUMNS,
            ),
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                ),
                CATEGORICAL_COLUMNS,
            ),
        ],
        remainder="drop",
    )

    return Pipeline(
        steps=[
            (
                "preprocess",
                preprocessing,
            ),
            (
                "classifier",
                LogisticRegression(
                    solver="lbfgs",
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


@pytest.fixture()
def model_path(
    tmp_path: Path,
) -> Path:
    dataframe = (
        _build_training_frame()
    )

    X = dataframe[
        [
            TEXT_COLUMN,
            *NUMERIC_COLUMNS,
            *CATEGORICAL_COLUMNS,
        ]
    ]

    y = dataframe[
        "target_state"
    ]

    pipeline = _build_pipeline()

    pipeline.fit(
        X,
        y,
    )

    path = (
        tmp_path
        / "ml-diagnosis-test.joblib"
    )

    artifact = {
        "artifact_type":
            "misconceptionos-baseline-state-classifier",

        "model_version":
            MODEL_VERSION,

        "feature_version":
            "features-test-v1",

        "pipeline":
            pipeline,

        "classes":
            sorted(
                y.unique().tolist()
            ),

        "feature_columns": {
            "text":
                TEXT_COLUMN,

            "numeric":
                NUMERIC_COLUMNS,

            "categorical":
                CATEGORICAL_COLUMNS,
        },
    }

    joblib.dump(
        artifact,
        path,
    )

    return path


@pytest.fixture()
def confident_rule() -> RulePrediction:
    return RulePrediction(
        state="confident",
        confidence=0.92,
        primary_misconception_id="M1",
        rule_score=0.95,
        model_version="rule-v1.9",
    )


@pytest.fixture()
def no_misconception_rule() -> RulePrediction:
    return RulePrediction(
        state="no_misconception",
        confidence=0.95,
        primary_misconception_id=None,
        rule_score=0.95,
        model_version="rule-v1.9",
    )


@pytest.fixture()
def misconception_attempt() -> dict[str, Any]:
    return {
        "attempt_id":
            "attempt-1",

        "problem_id":
            "problem-1",

        "written_reasoning": (
            "I will use binary search directly "
            "because checking the middle element "
            "lets me discard half."
        ),

        "normalized_reasoning":
            None,

        "source_code": (
            "left = 0\n"
            "right = len(arr) - 1\n"
            "while left <= right:\n"
            "    mid = (left + right) // 2"
        ),

        "speech_transcript":
            None,

        "selected_language":
            "python",

        "input_language":
            "english",

        "input_modality":
            "text + code",

        "response_time_seconds":
            44,
    }


@pytest.fixture()
def correct_attempt() -> dict[str, Any]:
    return {
        "attempt_id":
            "attempt-2",

        "problem_id":
            "problem-1",

        "written_reasoning": (
            "Binary search requires sorted input. "
            "This array is unsorted, so I will use "
            "linear search."
        ),

        "normalized_reasoning":
            None,

        "source_code": (
            "for i, value in enumerate(arr):\n"
            "    if value == target:\n"
            "        return i"
        ),

        "speech_transcript":
            None,

        "selected_language":
            "python",

        "input_language":
            "english",

        "input_modality":
            "text + code",

        "response_time_seconds":
            30,
    }


def test_build_attempt_ml_payload_injects_rule_context(
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    payload = build_attempt_ml_payload(
        misconception_attempt,
        rule_prediction=confident_rule,
    )

    assert (
        payload[
            "rule_state"
        ]
        == "confident"
    )

    assert (
        payload[
            "rule_confidence"
        ]
        == pytest.approx(
            0.92
        )
    )

    assert (
        payload[
            "rule_score"
        ]
        == pytest.approx(
            0.95
        )
    )

    assert (
        payload[
            "rule_misconception_id"
        ]
        == "M1"
    )


def test_build_attempt_ml_payload_preserves_attempt_fields(
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    payload = build_attempt_ml_payload(
        misconception_attempt,
        rule_prediction=confident_rule,
    )

    assert (
        payload[
            "written_reasoning"
        ]
        == misconception_attempt[
            "written_reasoning"
        ]
    )

    assert (
        payload[
            "source_code"
        ]
        == misconception_attempt[
            "source_code"
        ]
    )


def test_build_attempt_ml_payload_uses_confidence_when_rule_score_missing(
    misconception_attempt: dict[str, Any],
) -> None:
    rule = RulePrediction(
        state="possible",
        confidence=0.62,
        primary_misconception_id="M1",
        rule_score=None,
    )

    payload = build_attempt_ml_payload(
        misconception_attempt,
        rule_prediction=rule,
    )

    assert (
        payload[
            "rule_score"
        ]
        == pytest.approx(
            0.62
        )
    )


def test_build_attempt_ml_payload_requires_mapping(
    confident_rule: RulePrediction,
) -> None:
    with pytest.raises(
        TypeError,
        match="attempt must be a mapping",
    ):
        build_attempt_ml_payload(
            "invalid",  # type: ignore[arg-type]
            rule_prediction=confident_rule,
        )


def test_diagnose_with_ml_returns_structured_result(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    assert isinstance(
        result,
        MLDiagnosisServiceResult,
    )

    assert (
        result.service_version
        == ML_DIAGNOSIS_SERVICE_VERSION
    )

    assert (
        result.prediction_source
        == "hybrid"
    )

    assert (
        result.ml_model_version
        == MODEL_VERSION
    )

    assert (
        result.rule_model_version
        == "rule-v1.9"
    )


def test_diagnose_with_ml_confidence_is_valid_probability(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    assert (
        0.0
        <= result.confidence
        <= 1.0
    )

    assert (
        0.0
        <= result.ml_score
        <= 1.0
    )

    assert (
        0.0
        <= result.hybrid_score
        <= 1.0
    )


def test_diagnose_with_ml_misconception_state_has_misconception_id(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    if result.state in {
        "confident",
        "possible",
    }:
        assert (
            result.primary_misconception_id
            is not None
        )


def test_diagnose_with_ml_non_misconception_state_has_no_id(
    model_path: Path,
    correct_attempt: dict[str, Any],
    no_misconception_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=correct_attempt,
        rule_prediction=no_misconception_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    if result.state in {
        "insufficient",
        "no_misconception",
    }:
        assert (
            result.primary_misconception_id
            is None
        )


def test_diagnose_with_ml_assigns_existing_intervention_action(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    expected = {
        "confident":
            "show_hint",

        "possible":
            "ask_diagnostic_question",

        "insufficient":
            "ask_clarification",

        "no_misconception":
            "no_action",
    }

    assert (
        result.next_action
        == expected[
            result.state
        ]
    )


def test_diagnose_with_ml_returns_nested_ml_and_fusion_objects(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    assert (
        result.ml_prediction
        is not None
    )

    assert (
        result.fusion_result
        is not None
    )

    assert (
        result.fusion_result
        .prediction_source
        == "hybrid"
    )


def test_diagnose_with_ml_to_dict_is_serializable_contract(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    payload = result.to_dict()

    assert isinstance(
        payload,
        dict,
    )

    assert (
        payload[
            "prediction_source"
        ]
        == "hybrid"
    )

    assert isinstance(
        payload[
            "ml_prediction"
        ],
        dict,
    )

    assert isinstance(
        payload[
            "fusion_result"
        ],
        dict,
    )


def test_diagnose_with_ml_from_mapping_matches_direct_path(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    direct = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    mapped = diagnose_with_ml_from_mapping(
        attempt=misconception_attempt,
        rule_result={
            "state":
                confident_rule.state,

            "confidence":
                confident_rule.confidence,

            "primary_misconception_id":
                confident_rule
                .primary_misconception_id,

            "rule_score":
                confident_rule.rule_score,

            "model_version":
                confident_rule.model_version,
        },
        model_path=model_path,
        use_model_cache=False,
    )

    assert (
        mapped.state
        == direct.state
    )

    assert (
        mapped.primary_misconception_id
        == direct.primary_misconception_id
    )

    assert (
        mapped.ml_state
        == direct.ml_state
    )


def test_diagnosis_model_fields_contains_only_orm_ready_values(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    fields = diagnosis_model_fields(
        result
    )

    assert set(
        fields.keys()
    ) == {
        "state",
        "primary_misconception_id",
        "confidence",
        "model_version",
        "decision_reason",
        "next_action",
        "rule_score",
        "ml_score",
        "hybrid_score",
        "prediction_source",
        "feature_version",
        "calibration_version",
    }

    assert (
        "ml_prediction"
        not in fields
    )

    assert (
        "fusion_result"
        not in fields
    )


def test_diagnosis_model_fields_preserves_hybrid_metadata(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    fields = diagnosis_model_fields(
        result
    )

    assert (
        fields[
            "prediction_source"
        ]
        == "hybrid"
    )

    assert (
        fields[
            "ml_score"
        ]
        == pytest.approx(
            result.ml_score
        )
    )

    assert (
        fields[
            "hybrid_score"
        ]
        == pytest.approx(
            result.hybrid_score
        )
    )


def test_ml_diagnosis_available_true_for_existing_artifact(
    model_path: Path,
) -> None:
    availability = (
        ml_diagnosis_available(
            model_path
        )
    )

    assert (
        availability.available
        is True
    )

    assert (
        availability.reason
        is None
    )


def test_ml_diagnosis_available_false_for_missing_artifact(
    tmp_path: Path,
) -> None:
    missing_path = (
        tmp_path
        / "missing.joblib"
    )

    availability = (
        ml_diagnosis_available(
            missing_path
        )
    )

    assert (
        availability.available
        is False
    )

    assert (
        availability.reason
        is not None
    )


def test_rule_only_fields_for_confident_state() -> None:
    fields = (
        rule_only_diagnosis_model_fields(
            state="confident",
            confidence=0.92,
            primary_misconception_id="M1",
            decision_reason=(
                "Strong rule evidence."
            ),
            rule_score=0.95,
            model_version="rule-v1.9",
        )
    )

    assert (
        fields[
            "state"
        ]
        == "confident"
    )

    assert (
        fields[
            "primary_misconception_id"
        ]
        == "M1"
    )

    assert (
        fields[
            "next_action"
        ]
        == "show_hint"
    )

    assert (
        fields[
            "prediction_source"
        ]
        == "rule"
    )

    assert (
        fields[
            "ml_score"
        ]
        is None
    )

    assert (
        fields[
            "hybrid_score"
        ]
        is None
    )


def test_rule_only_fields_for_possible_state() -> None:
    fields = (
        rule_only_diagnosis_model_fields(
            state="possible",
            confidence=0.62,
            primary_misconception_id="M1",
            decision_reason=None,
            rule_score=0.64,
            model_version="rule-v1.9",
        )
    )

    assert (
        fields[
            "next_action"
        ]
        == "ask_diagnostic_question"
    )


def test_rule_only_fields_for_insufficient_state() -> None:
    fields = (
        rule_only_diagnosis_model_fields(
            state="insufficient",
            confidence=0.25,
            primary_misconception_id=None,
            decision_reason=None,
            rule_score=0.20,
            model_version="rule-v1.9",
        )
    )

    assert (
        fields[
            "next_action"
        ]
        == "ask_clarification"
    )

    assert (
        fields[
            "primary_misconception_id"
        ]
        is None
    )


def test_rule_only_fields_for_no_misconception_state() -> None:
    fields = (
        rule_only_diagnosis_model_fields(
            state="no_misconception",
            confidence=0.95,
            primary_misconception_id=None,
            decision_reason=None,
            rule_score=0.95,
            model_version="rule-v1.9",
        )
    )

    assert (
        fields[
            "next_action"
        ]
        == "no_action"
    )

    assert (
        fields[
            "primary_misconception_id"
        ]
        is None
    )


def test_rule_only_confident_requires_misconception_id() -> None:
    with pytest.raises(
        ValueError,
        match="requires a misconception ID",
    ):
        rule_only_diagnosis_model_fields(
            state="confident",
            confidence=0.90,
            primary_misconception_id=None,
            decision_reason=None,
            rule_score=0.90,
            model_version="rule-v1.9",
        )


def test_rule_only_possible_requires_misconception_id() -> None:
    with pytest.raises(
        ValueError,
        match="requires a misconception ID",
    ):
        rule_only_diagnosis_model_fields(
            state="possible",
            confidence=0.60,
            primary_misconception_id=None,
            decision_reason=None,
            rule_score=0.60,
            model_version="rule-v1.9",
        )


@pytest.mark.parametrize(
    "state",
    [
        "insufficient",
        "no_misconception",
    ],
)
def test_rule_only_non_misconception_states_reject_id(
    state: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "must not contain a "
            "misconception ID"
        ),
    ):
        rule_only_diagnosis_model_fields(
            state=state,
            confidence=(
                0.20
                if state
                == "insufficient"
                else 0.95
            ),
            primary_misconception_id="M1",
            decision_reason=None,
            rule_score=0.50,
            model_version="rule-v1.9",
        )


def test_rule_only_rejects_invalid_probability() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "confidence must be between "
            "0 and 1"
        ),
    ):
        rule_only_diagnosis_model_fields(
            state="confident",
            confidence=1.20,
            primary_misconception_id="M1",
            decision_reason=None,
            rule_score=0.95,
            model_version="rule-v1.9",
        )


def test_custom_fusion_config_is_used(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    config = FusionConfig(
        rule_weight=0.80,
        ml_weight=0.20,
    )

    result = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        fusion_config=config,
        use_model_cache=False,
    )

    assert (
        result.fusion_result
        .rule_weight
        == pytest.approx(
            0.80
        )
    )

    assert (
        result.fusion_result
        .ml_weight
        == pytest.approx(
            0.20
        )
    )


def test_telugu_multimodal_attempt_runs_through_service(
    model_path: Path,
    no_misconception_rule: RulePrediction,
) -> None:
    attempt = {
        "attempt_id":
            "attempt-telugu",

        "problem_id":
            "problem-1",

        "written_reasoning": (
            "ఈ array sorted కాదు. "
            "So direct binary search use చేయకూడదు. "
            "Linear search చేస్తాను."
        ),

        "source_code": (
            "for i, value in enumerate(arr):\n"
            "    if value == target:\n"
            "        return i"
        ),

        "speech_transcript": (
            "Binary search కి sorted order అవసరం."
        ),

        "selected_language":
            "python",

        "input_language":
            "telugu",

        "input_modality":
            "text + code + speech",

        "response_time_seconds":
            39,
    }

    result = diagnose_with_ml(
        attempt=attempt,
        rule_prediction=no_misconception_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    assert (
        0.0
        <= result.ml_confidence
        <= 1.0
    )

    assert (
        result.prediction_source
        == "hybrid"
    )


def test_service_is_deterministic_for_same_model_and_input(
    model_path: Path,
    misconception_attempt: dict[str, Any],
    confident_rule: RulePrediction,
) -> None:
    first = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    second = diagnose_with_ml(
        attempt=misconception_attempt,
        rule_prediction=confident_rule,
        model_path=model_path,
        use_model_cache=False,
    )

    assert (
        first.state
        == second.state
    )

    assert (
        first.confidence
        == pytest.approx(
            second.confidence,
            abs=1e-12,
        )
    )

    assert (
        first.ml_state
        == second.ml_state
    )