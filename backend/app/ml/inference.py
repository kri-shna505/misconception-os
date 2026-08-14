from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

import joblib
import pandas as pd

from app.ml.feature_builder import (
    build_feature_record_from_mapping,
    get_numeric_feature_dict,
)


# ---------------------------------------------------------------------------
# Artifact configuration
# ---------------------------------------------------------------------------

BACKEND_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DEFAULT_MODEL_PATH = (
    BACKEND_ROOT
    / "ml"
    / "models"
    / "baseline"
    / "baseline_logistic_regression.joblib"
)

EXPECTED_ARTIFACT_TYPE = (
    "misconceptionos-baseline-state-classifier"
)

SUPPORTED_MODEL_VERSION_PREFIX = (
    "baseline-logreg-"
)


# ---------------------------------------------------------------------------
# Public result contracts
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ClassProbability:
    """
    Probability assigned to one diagnosis-state class.
    """

    label: str
    probability: float


@dataclass(slots=True, frozen=True)
class BaselinePrediction:
    """
    Runtime output produced by the Sprint 11 baseline model.

    This object intentionally does not decide the final diagnosis.

    The hybrid diagnosis service will later combine:

    - rule output;
    - ML prediction;
    - code/evidence signals;
    - calibrated confidence.

    This module is therefore ML inference only.
    """

    predicted_state: str
    confidence: float

    probabilities: tuple[
        ClassProbability,
        ...
    ]

    model_version: str
    feature_version: str | None

    prediction_source: str = "ml"

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "predicted_state":
                self.predicted_state,

            "confidence":
                self.confidence,

            "probabilities": [
                asdict(item)
                for item
                in self.probabilities
            ],

            "model_version":
                self.model_version,

            "feature_version":
                self.feature_version,

            "prediction_source":
                self.prediction_source,
        }


# ---------------------------------------------------------------------------
# Artifact wrapper
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LoadedBaselineArtifact:
    """
    Validated baseline model artifact loaded from disk.
    """

    model_version: str

    pipeline: Any

    classes: tuple[
        str,
        ...
    ]

    text_column: str

    numeric_columns: tuple[
        str,
        ...
    ]

    categorical_columns: tuple[
        str,
        ...
    ]

    feature_version: str | None = None

    artifact_type: str | None = None


# ---------------------------------------------------------------------------
# In-memory artifact cache
# ---------------------------------------------------------------------------

_ARTIFACT_CACHE: dict[
    Path,
    LoadedBaselineArtifact,
] = {}

_ARTIFACT_CACHE_LOCK = Lock()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _normalize_model_path(
    model_path: Path | str | None,
) -> Path:
    if model_path is None:
        path = DEFAULT_MODEL_PATH
    else:
        path = Path(
            model_path
        )

    return (
        path
        .expanduser()
        .resolve()
    )


def _require_mapping(
    value: Any,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise ValueError(
            f"{field_name} must be a mapping."
        )

    return value


def _require_non_blank_string(
    value: Any,
    *,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            f"{field_name} must be a string."
        )

    normalized = (
        value.strip()
    )

    if not normalized:
        raise ValueError(
            f"{field_name} must not be blank."
        )

    return normalized


def _normalize_string_sequence(
    value: Any,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        raise ValueError(
            f"{field_name} must be a list "
            "or tuple."
        )

    normalized: list[str] = []

    for item in value:
        normalized.append(
            _require_non_blank_string(
                item,
                field_name=field_name,
            )
        )

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return tuple(
        normalized
    )


def _validate_pipeline_contract(
    pipeline: Any,
) -> None:
    if not hasattr(
        pipeline,
        "predict",
    ):
        raise ValueError(
            "Loaded baseline pipeline does not "
            "provide predict()."
        )

    if not hasattr(
        pipeline,
        "predict_proba",
    ):
        raise ValueError(
            "Loaded baseline pipeline does not "
            "provide predict_proba()."
        )


def _parse_loaded_artifact(
    raw_artifact: Any,
) -> LoadedBaselineArtifact:
    artifact = _require_mapping(
        raw_artifact,
        field_name="model artifact",
    )

    model_version = (
        _require_non_blank_string(
            artifact.get(
                "model_version"
            ),
            field_name=(
                "artifact.model_version"
            ),
        )
    )

    if not model_version.startswith(
        SUPPORTED_MODEL_VERSION_PREFIX
    ):
        raise ValueError(
            "Unsupported baseline model version: "
            f"{model_version!r}."
        )

    artifact_type_value = (
        artifact.get(
            "artifact_type"
        )
    )

    artifact_type: str | None

    if artifact_type_value is None:
        # Older smoke artifact compatibility.
        artifact_type = None

    else:
        artifact_type = (
            _require_non_blank_string(
                artifact_type_value,
                field_name=(
                    "artifact.artifact_type"
                ),
            )
        )

        if (
            artifact_type
            != EXPECTED_ARTIFACT_TYPE
        ):
            raise ValueError(
                "Unexpected model artifact type: "
                f"{artifact_type!r}."
            )

    pipeline = artifact.get(
        "pipeline"
    )

    if pipeline is None:
        raise ValueError(
            "Model artifact does not contain "
            "'pipeline'."
        )

    _validate_pipeline_contract(
        pipeline
    )

    classes = (
        _normalize_string_sequence(
            artifact.get(
                "classes"
            ),
            field_name=(
                "artifact.classes"
            ),
        )
    )

    feature_columns = (
        _require_mapping(
            artifact.get(
                "feature_columns"
            ),
            field_name=(
                "artifact.feature_columns"
            ),
        )
    )

    text_column = (
        _require_non_blank_string(
            feature_columns.get(
                "text"
            ),
            field_name=(
                "feature_columns.text"
            ),
        )
    )

    numeric_columns = (
        _normalize_string_sequence(
            feature_columns.get(
                "numeric"
            ),
            field_name=(
                "feature_columns.numeric"
            ),
        )
    )

    categorical_columns = (
        _normalize_string_sequence(
            feature_columns.get(
                "categorical"
            ),
            field_name=(
                "feature_columns.categorical"
            ),
        )
    )

    feature_version_value = (
        artifact.get(
            "feature_version"
        )
    )

    feature_version: str | None

    if feature_version_value is None:
        feature_version = None
    else:
        feature_version = (
            str(
                feature_version_value
            )
            .strip()
            or None
        )

    return LoadedBaselineArtifact(
        model_version=(
            model_version
        ),

        pipeline=pipeline,

        classes=classes,

        text_column=(
            text_column
        ),

        numeric_columns=(
            numeric_columns
        ),

        categorical_columns=(
            categorical_columns
        ),

        feature_version=(
            feature_version
        ),

        artifact_type=(
            artifact_type
        ),
    )


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def load_baseline_artifact(
    model_path: Path | str | None = None,
    *,
    use_cache: bool = True,
) -> LoadedBaselineArtifact:
    """
    Load and validate the trained baseline artifact.

    Artifacts are cached by resolved path so normal API inference does
    not deserialize the model on every request.
    """

    path = _normalize_model_path(
        model_path
    )

    if not path.exists():
        raise FileNotFoundError(
            "Baseline model artifact not found: "
            f"{path}"
        )

    if not path.is_file():
        raise FileNotFoundError(
            "Baseline model artifact path is "
            f"not a file: {path}"
        )

    if use_cache:
        with _ARTIFACT_CACHE_LOCK:
            cached = (
                _ARTIFACT_CACHE.get(
                    path
                )
            )

            if cached is not None:
                return cached

    raw_artifact = joblib.load(
        path
    )

    loaded = (
        _parse_loaded_artifact(
            raw_artifact
        )
    )

    if use_cache:
        with _ARTIFACT_CACHE_LOCK:
            _ARTIFACT_CACHE[
                path
            ] = loaded

    return loaded


def clear_model_cache() -> None:
    """
    Clear the process-local ML model cache.

    Useful in tests and during model replacement.
    """

    with _ARTIFACT_CACHE_LOCK:
        _ARTIFACT_CACHE.clear()


# ---------------------------------------------------------------------------
# Feature preparation
# ---------------------------------------------------------------------------


def _feature_record_to_mapping(
    raw_attempt: Mapping[str, Any],
    *,
    artifact: LoadedBaselineArtifact,
) -> dict[str, Any]:
    """
    Convert one attempt into the exact dataframe structure expected by
    the saved sklearn pipeline.

    Crucially, this uses the same app.ml.feature_builder contract that
    offline training uses.
    """

    feature_record = (
        build_feature_record_from_mapping(
            raw_attempt
        )
    )

    numeric_features = (
        get_numeric_feature_dict(
            feature_record
        )
    )

    feature_mapping: dict[
        str,
        Any,
    ] = {}

    feature_mapping[
        artifact.text_column
    ] = (
        feature_record.combined_text
        or ""
    )

    categorical_values = {
        "selected_language":
            feature_record.selected_language,

        "input_language":
            feature_record.input_language,

        "input_modality":
            feature_record.input_modality,

        "rule_state":
            feature_record.rule_state,

        "rule_misconception_id":
            feature_record.rule_misconception_id,
    }

    for column in (
        artifact.numeric_columns
    ):
        value = (
            numeric_features.get(
                column,
                0.0,
            )
        )

        if value is None:
            value = 0.0

        feature_mapping[
            column
        ] = float(
            value
        )

    for column in (
        artifact.categorical_columns
    ):
        value = (
            categorical_values.get(
                column
            )
        )

        if value is None:
            normalized = "missing"
        else:
            normalized = (
                str(value)
                .strip()
                or "missing"
            )

        feature_mapping[
            column
        ] = normalized

    return feature_mapping


def build_inference_dataframe(
    raw_attempt: Mapping[str, Any],
    *,
    artifact: LoadedBaselineArtifact,
) -> pd.DataFrame:
    """
    Build a one-row dataframe accepted by the persisted sklearn
    pipeline.
    """

    feature_mapping = (
        _feature_record_to_mapping(
            raw_attempt,
            artifact=artifact,
        )
    )

    ordered_columns = [
        artifact.text_column,
        *artifact.numeric_columns,
        *artifact.categorical_columns,
    ]

    return pd.DataFrame(
        [
            feature_mapping
        ],
        columns=ordered_columns,
    )


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------


def _get_pipeline_classes(
    artifact: LoadedBaselineArtifact,
) -> tuple[str, ...]:
    """
    Prefer the fitted classifier's class ordering because predict_proba
    follows that ordering.
    """

    pipeline = artifact.pipeline

    classes_value = getattr(
        pipeline,
        "classes_",
        None,
    )

    if classes_value is None:
        classifier = None

        if hasattr(
            pipeline,
            "named_steps",
        ):
            classifier = (
                pipeline
                .named_steps
                .get(
                    "classifier"
                )
            )

        classes_value = getattr(
            classifier,
            "classes_",
            None,
        )

    if classes_value is None:
        return (
            artifact.classes
        )

    classes = tuple(
        str(value)
        for value
        in classes_value
    )

    if not classes:
        raise RuntimeError(
            "Fitted classifier exposes an "
            "empty class list."
        )

    return classes


def _normalize_probability(
    value: Any,
) -> float:
    probability = float(
        value
    )

    # Defensive numerical cleanup.
    if probability < 0.0:
        return 0.0

    if probability > 1.0:
        return 1.0

    return probability


# ---------------------------------------------------------------------------
# Public inference API
# ---------------------------------------------------------------------------


def predict_baseline(
    raw_attempt: Mapping[str, Any],
    *,
    model_path: Path | str | None = None,
    use_cache: bool = True,
) -> BaselinePrediction:
    """
    Run the saved baseline model against one attempt.

    raw_attempt should contain the same raw fields used by the Sprint 11
    feature builder, for example:

    written_reasoning
    normalized_reasoning
    source_code
    speech_transcript
    selected_language
    input_language
    input_modality
    response_time_seconds
    rule_state
    rule_misconception_id
    rule_confidence
    rule_score

    Missing optional fields are handled by the feature builder.
    """

    if not isinstance(
        raw_attempt,
        Mapping,
    ):
        raise TypeError(
            "raw_attempt must be a mapping."
        )

    artifact = (
        load_baseline_artifact(
            model_path,
            use_cache=use_cache,
        )
    )

    dataframe = (
        build_inference_dataframe(
            raw_attempt,
            artifact=artifact,
        )
    )

    prediction_values = (
        artifact.pipeline.predict(
            dataframe
        )
    )

    if len(
        prediction_values
    ) != 1:
        raise RuntimeError(
            "Baseline inference returned an "
            "unexpected prediction shape."
        )

    predicted_state = str(
        prediction_values[0]
    )

    probability_matrix = (
        artifact.pipeline.predict_proba(
            dataframe
        )
    )

    if len(
        probability_matrix
    ) != 1:
        raise RuntimeError(
            "Baseline inference returned an "
            "unexpected probability shape."
        )

    probabilities_raw = (
        probability_matrix[0]
    )

    classes = (
        _get_pipeline_classes(
            artifact
        )
    )

    if (
        len(classes)
        != len(
            probabilities_raw
        )
    ):
        raise RuntimeError(
            "Model class count does not match "
            "predict_proba output."
        )

    class_probabilities = tuple(
        ClassProbability(
            label=label,
            probability=(
                _normalize_probability(
                    probability
                )
            ),
        )
        for (
            label,
            probability,
        )
        in zip(
            classes,
            probabilities_raw,
            strict=True,
        )
    )

    probability_lookup = {
        item.label:
            item.probability
        for item
        in class_probabilities
    }

    if (
        predicted_state
        not in probability_lookup
    ):
        raise RuntimeError(
            "Predicted class was not present "
            "in probability output."
        )

    confidence = (
        probability_lookup[
            predicted_state
        ]
    )

    ordered_probabilities = tuple(
        sorted(
            class_probabilities,
            key=lambda item: (
                item.probability
            ),
            reverse=True,
        )
    )

    return BaselinePrediction(
        predicted_state=(
            predicted_state
        ),

        confidence=(
            confidence
        ),

        probabilities=(
            ordered_probabilities
        ),

        model_version=(
            artifact.model_version
        ),

        feature_version=(
            artifact.feature_version
        ),

        prediction_source="ml",
    )


def predict_baseline_dict(
    raw_attempt: Mapping[str, Any],
    *,
    model_path: Path | str | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Convenience wrapper for API/service layers that prefer dictionaries.
    """

    return (
        predict_baseline(
            raw_attempt,
            model_path=model_path,
            use_cache=use_cache,
        )
        .to_dict()
    )


def baseline_model_available(
    model_path: Path | str | None = None,
) -> bool:
    """
    Return whether the configured baseline model artifact exists.

    This intentionally checks availability only; it does not swallow
    artifact-validation errors during real inference.
    """

    path = (
        _normalize_model_path(
            model_path
        )
    )

    return (
        path.exists()
        and path.is_file()
    )


__all__ = [
    "BACKEND_ROOT",
    "DEFAULT_MODEL_PATH",
    "EXPECTED_ARTIFACT_TYPE",
    "SUPPORTED_MODEL_VERSION_PREFIX",
    "ClassProbability",
    "BaselinePrediction",
    "LoadedBaselineArtifact",
    "load_baseline_artifact",
    "clear_model_cache",
    "build_inference_dataframe",
    "predict_baseline",
    "predict_baseline_dict",
    "baseline_model_available",
]