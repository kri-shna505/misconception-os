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

from app.ml.inference import (
    EXPECTED_ARTIFACT_TYPE,
    BaselinePrediction,
    baseline_model_available,
    build_inference_dataframe,
    clear_model_cache,
    load_baseline_artifact,
    predict_baseline,
    predict_baseline_dict,
)


MODEL_VERSION = "baseline-logreg-test-v1.0"


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
        "combined_text":
            combined_text,

        "response_time_seconds":
            response_time_seconds,

        "has_reasoning":
            has_reasoning,

        "has_code":
            has_code,

        "has_speech":
            has_speech,

        "reasoning_length":
            reasoning_length,

        "source_code_length":
            source_code_length,

        "speech_length":
            speech_length,

        "combined_text_length":
            float(
                len(
                    combined_text
                )
            ),

        "rule_confidence":
            rule_confidence,

        "rule_score":
            rule_score,

        "selected_language":
            selected_language,

        "input_language":
            input_language,

        "input_modality":
            input_modality,

        "rule_state":
            rule_state,

        "rule_misconception_id":
            rule_misconception_id,

        "target_state":
            target_state,
    }


def _build_test_training_frame() -> pd.DataFrame:
    rows = [
        _training_row(
            combined_text=(
                "Binary search requires sorted input. "
                "The array is unsorted, so I will use "
                "linear search."
            ),
            response_time_seconds=30,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=85,
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
                "This input is not sorted. "
                "I should scan every element."
            ),
            response_time_seconds=35,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=60,
            source_code_length=55,
            speech_length=0,
            rule_confidence=0.92,
            rule_score=0.91,
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
                "కాబట్టి linear search use చేస్తాను."
            ),
            response_time_seconds=40,
            has_reasoning=1,
            has_code=1,
            has_speech=1,
            reasoning_length=52,
            source_code_length=60,
            speech_length=35,
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
                "and repeatedly discard half."
            ),
            response_time_seconds=45,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=68,
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
                "Binary search should work even though "
                "the array is not sorted."
            ),
            response_time_seconds=42,
            has_reasoning=1,
            has_code=1,
            has_speech=1,
            reasoning_length=65,
            source_code_length=90,
            speech_length=50,
            rule_confidence=0.93,
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
                "Array order check చేయాల్సిన అవసరం లేదు. "
                "Binary search faster."
            ),
            response_time_seconds=44,
            has_reasoning=1,
            has_code=1,
            has_speech=0,
            reasoning_length=62,
            source_code_length=80,
            speech_length=0,
            rule_confidence=0.90,
            rule_score=0.92,
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
                "Maybe compare with the middle element. "
                "I am unsure whether sorted order matters."
            ),
            response_time_seconds=29,
            has_reasoning=1,
            has_code=0,
            has_speech=1,
            reasoning_length=82,
            source_code_length=0,
            speech_length=42,
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
            rule_confidence=0.59,
            rule_score=0.61,
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

    return pd.DataFrame(
        rows
    )


def _build_test_pipeline() -> Pipeline:
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
        _build_test_training_frame()
    )

    feature_columns = [
        TEXT_COLUMN,
        *NUMERIC_COLUMNS,
        *CATEGORICAL_COLUMNS,
    ]

    X = dataframe[
        feature_columns
    ]

    y = dataframe[
        "target_state"
    ]

    pipeline = (
        _build_test_pipeline()
    )

    pipeline.fit(
        X,
        y,
    )

    path = (
        tmp_path
        / "baseline_test.joblib"
    )

    artifact = {
        "artifact_type":
            EXPECTED_ARTIFACT_TYPE,

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

    clear_model_cache()

    return path


@pytest.fixture()
def correct_attempt() -> dict[str, Any]:
    return {
        "written_reasoning": (
            "Binary search requires sorted input. "
            "This array is not sorted, so I will "
            "use linear search."
        ),

        "normalized_reasoning": None,

        "source_code": (
            "def search(arr, target):\n"
            "    for index, value in enumerate(arr):\n"
            "        if value == target:\n"
            "            return index\n"
            "    return -1"
        ),

        "speech_transcript": None,

        "selected_language":
            "python",

        "input_language":
            "english",

        "input_modality":
            "text + code",

        "response_time_seconds":
            30,

        "rule_state":
            "no_misconception",

        "rule_misconception_id":
            None,

        "rule_confidence":
            0.95,

        "rule_score":
            0.95,
    }


@pytest.fixture()
def misconception_attempt() -> dict[str, Any]:
    return {
        "written_reasoning": (
            "I will use binary search directly "
            "because checking the middle element "
            "lets me discard half the array."
        ),

        "normalized_reasoning":
            None,

        "source_code": (
            "left = 0\n"
            "right = len(arr) - 1\n"
            "while left <= right:\n"
            "    mid = (left + right) // 2\n"
            "    if arr[mid] < target:\n"
            "        left = mid + 1"
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

        "rule_state":
            "confident",

        "rule_misconception_id":
            "M1",

        "rule_confidence":
            0.92,

        "rule_score":
            0.95,
    }


def test_baseline_model_available_returns_true_for_existing_artifact(
    model_path: Path,
) -> None:
    assert (
        baseline_model_available(
            model_path
        )
        is True
    )


def test_baseline_model_available_returns_false_for_missing_artifact(
    tmp_path: Path,
) -> None:
    missing_path = (
        tmp_path
        / "missing-model.joblib"
    )

    assert (
        baseline_model_available(
            missing_path
        )
        is False
    )


def test_load_baseline_artifact_returns_validated_contract(
    model_path: Path,
) -> None:
    artifact = (
        load_baseline_artifact(
            model_path,
            use_cache=False,
        )
    )

    assert (
        artifact.model_version
        == MODEL_VERSION
    )

    assert (
        artifact.artifact_type
        == EXPECTED_ARTIFACT_TYPE
    )

    assert (
        artifact.feature_version
        == "features-test-v1"
    )

    assert (
        artifact.text_column
        == TEXT_COLUMN
    )

    assert (
        artifact.numeric_columns
        == tuple(
            NUMERIC_COLUMNS
        )
    )

    assert (
        artifact.categorical_columns
        == tuple(
            CATEGORICAL_COLUMNS
        )
    )

    assert (
        len(
            artifact.classes
        )
        == 4
    )


def test_load_baseline_artifact_raises_when_file_is_missing(
    tmp_path: Path,
) -> None:
    missing_path = (
        tmp_path
        / "does-not-exist.joblib"
    )

    with pytest.raises(
        FileNotFoundError,
        match=(
            "Baseline model artifact "
            "not found"
        ),
    ):
        load_baseline_artifact(
            missing_path,
            use_cache=False,
        )


def test_load_baseline_artifact_rejects_wrong_artifact_type(
    model_path: Path,
    tmp_path: Path,
) -> None:
    raw = joblib.load(
        model_path
    )

    raw["artifact_type"] = (
        "wrong-artifact-type"
    )

    bad_path = (
        tmp_path
        / "wrong-artifact.joblib"
    )

    joblib.dump(
        raw,
        bad_path,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unexpected model artifact type"
        ),
    ):
        load_baseline_artifact(
            bad_path,
            use_cache=False,
        )


def test_load_baseline_artifact_rejects_unsupported_model_version(
    model_path: Path,
    tmp_path: Path,
) -> None:
    raw = joblib.load(
        model_path
    )

    raw["model_version"] = (
        "transformer-test-v1"
    )

    bad_path = (
        tmp_path
        / "unsupported-version.joblib"
    )

    joblib.dump(
        raw,
        bad_path,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unsupported baseline model version"
        ),
    ):
        load_baseline_artifact(
            bad_path,
            use_cache=False,
        )


def test_load_baseline_artifact_rejects_missing_pipeline(
    model_path: Path,
    tmp_path: Path,
) -> None:
    raw = joblib.load(
        model_path
    )

    raw.pop(
        "pipeline"
    )

    bad_path = (
        tmp_path
        / "missing-pipeline.joblib"
    )

    joblib.dump(
        raw,
        bad_path,
    )

    with pytest.raises(
        ValueError,
        match=(
            "does not contain 'pipeline'"
        ),
    ):
        load_baseline_artifact(
            bad_path,
            use_cache=False,
        )


def test_build_inference_dataframe_returns_one_row(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    artifact = (
        load_baseline_artifact(
            model_path,
            use_cache=False,
        )
    )

    dataframe = (
        build_inference_dataframe(
            correct_attempt,
            artifact=artifact,
        )
    )

    assert isinstance(
        dataframe,
        pd.DataFrame,
    )

    assert len(
        dataframe
    ) == 1

    expected_columns = [
        TEXT_COLUMN,
        *NUMERIC_COLUMNS,
        *CATEGORICAL_COLUMNS,
    ]

    assert (
        dataframe.columns.tolist()
        == expected_columns
    )


def test_build_inference_dataframe_contains_text(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    artifact = (
        load_baseline_artifact(
            model_path,
            use_cache=False,
        )
    )

    dataframe = (
        build_inference_dataframe(
            correct_attempt,
            artifact=artifact,
        )
    )

    combined_text = str(
        dataframe.iloc[0][
            TEXT_COLUMN
        ]
    )

    assert (
        "Binary search requires sorted input"
        in combined_text
    )


def test_build_inference_dataframe_preserves_language_metadata(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    artifact = (
        load_baseline_artifact(
            model_path,
            use_cache=False,
        )
    )

    dataframe = (
        build_inference_dataframe(
            correct_attempt,
            artifact=artifact,
        )
    )

    row = dataframe.iloc[0]

    assert (
        row[
            "selected_language"
        ]
        == "python"
    )

    assert (
        row[
            "input_language"
        ]
        == "english"
    )

    assert (
        row[
            "input_modality"
        ]
        == "text + code"
    )


def test_build_inference_dataframe_preserves_rule_context(
    model_path: Path,
    misconception_attempt: dict[str, Any],
) -> None:
    artifact = (
        load_baseline_artifact(
            model_path,
            use_cache=False,
        )
    )

    dataframe = (
        build_inference_dataframe(
            misconception_attempt,
            artifact=artifact,
        )
    )

    row = dataframe.iloc[0]

    assert (
        row[
            "rule_state"
        ]
        == "confident"
    )

    assert (
        row[
            "rule_misconception_id"
        ]
        == "M1"
    )


def test_predict_baseline_returns_structured_prediction(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    result = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    assert isinstance(
        result,
        BaselinePrediction,
    )

    assert result.predicted_state in {
        "confident",
        "possible",
        "insufficient",
        "no_misconception",
    }

    assert (
        0.0
        <= result.confidence
        <= 1.0
    )

    assert (
        result.model_version
        == MODEL_VERSION
    )

    assert (
        result.feature_version
        == "features-test-v1"
    )

    assert (
        result.prediction_source
        == "ml"
    )


def test_predict_baseline_returns_probability_for_every_class(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    result = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    labels = {
        item.label
        for item
        in result.probabilities
    }

    assert labels == {
        "confident",
        "possible",
        "insufficient",
        "no_misconception",
    }


def test_predict_baseline_probabilities_are_valid(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    result = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    probabilities = [
        item.probability
        for item
        in result.probabilities
    ]

    assert all(
        0.0 <= value <= 1.0
        for value
        in probabilities
    )

    assert sum(
        probabilities
    ) == pytest.approx(
        1.0,
        abs=1e-6,
    )


def test_predict_baseline_confidence_matches_predicted_class_probability(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    result = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    probability_lookup = {
        item.label:
            item.probability
        for item
        in result.probabilities
    }

    assert (
        result.confidence
        == pytest.approx(
            probability_lookup[
                result.predicted_state
            ],
            abs=1e-9,
        )
    )


def test_predict_baseline_orders_probabilities_descending(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    result = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    values = [
        item.probability
        for item
        in result.probabilities
    ]

    assert values == sorted(
        values,
        reverse=True,
    )


def test_predict_baseline_is_deterministic(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    first = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    second = predict_baseline(
        correct_attempt,
        model_path=model_path,
        use_cache=False,
    )

    assert (
        first.predicted_state
        == second.predicted_state
    )

    assert (
        first.confidence
        == pytest.approx(
            second.confidence,
            abs=1e-12,
        )
    )

    assert (
        first.probabilities
        == second.probabilities
    )


def test_predict_baseline_dict_returns_serializable_contract(
    model_path: Path,
    correct_attempt: dict[str, Any],
) -> None:
    result = (
        predict_baseline_dict(
            correct_attempt,
            model_path=model_path,
            use_cache=False,
        )
    )

    assert isinstance(
        result,
        dict,
    )

    assert {
        "predicted_state",
        "confidence",
        "probabilities",
        "model_version",
        "feature_version",
        "prediction_source",
    }.issubset(
        result.keys()
    )

    assert (
        result[
            "prediction_source"
        ]
        == "ml"
    )

    assert isinstance(
        result[
            "probabilities"
        ],
        list,
    )


def test_predict_baseline_rejects_non_mapping_input(
    model_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "raw_attempt must be a mapping"
        ),
    ):
        predict_baseline(
            "not-a-mapping",  # type: ignore[arg-type]
            model_path=model_path,
            use_cache=False,
        )


def test_prediction_handles_missing_optional_fields(
    model_path: Path,
) -> None:
    attempt = {
        "written_reasoning":
            "I am not sure.",

        "selected_language":
            "python",

        "input_language":
            "english",

        "input_modality":
            "text",

        "response_time_seconds":
            10,

        "rule_state":
            "insufficient",

        "rule_confidence":
            0.20,

        "rule_score":
            0.15,
    }

    result = predict_baseline(
        attempt,
        model_path=model_path,
        use_cache=False,
    )

    assert (
        result.predicted_state
        in {
            "confident",
            "possible",
            "insufficient",
            "no_misconception",
        }
    )


def test_prediction_handles_telugu_code_switch_input(
    model_path: Path,
) -> None:
    attempt = {
        "written_reasoning": (
            "ఈ array sorted కాదు, "
            "so binary search direct ga use చేయకూడదు. "
            "I will use linear search."
        ),

        "source_code": (
            "for i, value in enumerate(arr):\n"
            "    if value == target:\n"
            "        return i"
        ),

        "speech_transcript": (
            "Sorted order లేకపోతే "
            "linear search safer."
        ),

        "selected_language":
            "python",

        "input_language":
            "telugu",

        "input_modality":
            "text + code + speech",

        "response_time_seconds":
            37,

        "rule_state":
            "no_misconception",

        "rule_misconception_id":
            None,

        "rule_confidence":
            0.95,

        "rule_score":
            0.95,
    }

    result = predict_baseline(
        attempt,
        model_path=model_path,
        use_cache=False,
    )

    assert (
        0.0
        <= result.confidence
        <= 1.0
    )

    assert (
        len(
            result.probabilities
        )
        == 4
    )


def test_prediction_handles_text_code_speech_modality(
    model_path: Path,
) -> None:
    attempt = {
        "written_reasoning": (
            "Binary search should work directly."
        ),

        "source_code": (
            "mid = (left + right) // 2"
        ),

        "speech_transcript": (
            "I can discard half after every comparison."
        ),

        "selected_language":
            "python",

        "input_language":
            "english",

        "input_modality":
            "text + code + speech",

        "response_time_seconds":
            42,

        "rule_state":
            "confident",

        "rule_misconception_id":
            "M1",

        "rule_confidence":
            0.92,

        "rule_score":
            0.95,
    }

    result = predict_baseline(
        attempt,
        model_path=model_path,
        use_cache=False,
    )

    assert (
        result.prediction_source
        == "ml"
    )


def test_model_cache_returns_same_loaded_artifact_instance(
    model_path: Path,
) -> None:
    clear_model_cache()

    first = (
        load_baseline_artifact(
            model_path,
            use_cache=True,
        )
    )

    second = (
        load_baseline_artifact(
            model_path,
            use_cache=True,
        )
    )

    assert first is second


def test_clear_model_cache_forces_reload(
    model_path: Path,
) -> None:
    clear_model_cache()

    first = (
        load_baseline_artifact(
            model_path,
            use_cache=True,
        )
    )

    clear_model_cache()

    second = (
        load_baseline_artifact(
            model_path,
            use_cache=True,
        )
    )

    assert (
        first is not second
    )


def test_corrupt_joblib_artifact_fails_cleanly(
    tmp_path: Path,
) -> None:
    corrupt_path = (
        tmp_path
        / "corrupt.joblib"
    )

    corrupt_path.write_bytes(
        b"this-is-not-a-valid-joblib-model"
    )

    with pytest.raises(
        Exception,
    ):
        load_baseline_artifact(
            corrupt_path,
            use_cache=False,
        )