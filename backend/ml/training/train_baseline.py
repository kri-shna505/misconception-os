from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "exports"
    / "teacher_reviewed_dataset.csv"
)

MODEL_DIR = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "baseline"
)

MODEL_PATH = (
    MODEL_DIR
    / "baseline_logistic_regression.joblib"
)

METRICS_PATH = (
    MODEL_DIR
    / "baseline_metrics.json"
)

MODEL_VERSION = "baseline-logreg-v1.1"

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

TARGET_COLUMN = "target_state"


@dataclass(slots=True)
class BaselineTrainingResult:
    model_version: str
    dataset_path: str

    total_rows: int
    train_rows: int
    test_rows: int

    classes: list[str]

    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float

    classification_report: dict[str, Any]
    confusion_matrix: list[list[int]]

    model_path: str
    metrics_path: str

    serious_training_ready: bool


def _ensure_required_columns(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = {
        TEXT_COLUMN,
        TARGET_COLUMN,
        *NUMERIC_COLUMNS,
        *CATEGORICAL_COLUMNS,
    }

    missing = sorted(
        required_columns
        - set(dataframe.columns)
    )

    if missing:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(missing)
        )


def _prepare_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert raw exported attempt rows into the feature contract
    expected by the baseline model.

    Feature construction remains centralized in
    app.ml.feature_builder so offline training and runtime
    inference use the same representation.
    """

    from app.ml.feature_builder import (
        build_feature_record_from_mapping,
        get_numeric_feature_dict,
    )

    df = dataframe.copy()

    enriched_rows: list[
        dict[str, Any]
    ] = []

    for raw_row in df.to_dict(
        orient="records"
    ):
        features = (
            build_feature_record_from_mapping(
                raw_row
            )
        )

        numeric_features = (
            get_numeric_feature_dict(
                features
            )
        )

        enriched_row = dict(
            raw_row
        )

        enriched_row.update(
            {
                "combined_text":
                    features.combined_text,

                "selected_language":
                    features.selected_language,

                "input_language":
                    features.input_language,

                "input_modality":
                    features.input_modality,

                "rule_state":
                    features.rule_state,

                "rule_misconception_id":
                    features.rule_misconception_id,
            }
        )

        enriched_row.update(
            numeric_features
        )

        enriched_rows.append(
            enriched_row
        )

    df = pd.DataFrame(
        enriched_rows
    )

    _ensure_required_columns(
        df
    )

    df[TEXT_COLUMN] = (
        df[TEXT_COLUMN]
        .fillna("")
        .astype(str)
    )

    for column in CATEGORICAL_COLUMNS:
        df[column] = (
            df[column]
            .fillna("missing")
            .astype(str)
            .str.strip()
            .replace(
                "",
                "missing",
            )
        )

    for column in NUMERIC_COLUMNS:
        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
            .fillna(0.0)
        )

    df[TARGET_COLUMN] = (
        df[TARGET_COLUMN]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df[
        df[TARGET_COLUMN] != ""
    ].copy()

    return df


def _validate_training_readiness(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate only the minimum requirements necessary
    to perform a stratified engineering baseline split.

    This does not imply that the dataset is large enough
    for scientifically meaningful evaluation.
    """

    if dataframe.empty:
        raise ValueError(
            "No supervised rows are available for training."
        )

    class_counts = (
        dataframe[TARGET_COLUMN]
        .value_counts()
    )

    if len(class_counts) < 2:
        raise ValueError(
            "Baseline classifier requires at least "
            "two target classes."
        )

    if class_counts.min() < 2:
        raise ValueError(
            "Every target class needs at least two "
            "examples for a stratified train/test split."
        )


def _build_pipeline() -> Pipeline:
    """
    Build the baseline state-classification pipeline.

    The target_state task is multiclass, so the classifier
    must support more than two classes.

    lbfgs is used instead of liblinear because liblinear
    cannot directly fit this four-class state prediction
    problem in the current scikit-learn configuration.
    """

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=5000,
                    sublinear_tf=True,
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

    classifier = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=42,
    )

    return Pipeline(
        steps=[
            (
                "preprocess",
                preprocessing,
            ),
            (
                "classifier",
                classifier,
            ),
        ]
    )


def _safe_test_size(
    total_rows: int,
    class_count: int,
) -> int:
    """
    Select an integer test size that permits a stratified
    split while giving every class a chance to appear in
    both train and test partitions.

    This logic exists primarily for the engineering
    smoke dataset.
    """

    preferred = max(
        class_count,
        round(
            total_rows * 0.25
        ),
    )

    maximum = (
        total_rows
        - class_count
    )

    if maximum < class_count:
        raise ValueError(
            "Dataset is too small for a stratified split "
            "with at least one train and test sample "
            "per class."
        )

    return min(
        preferred,
        maximum,
    )


def train_baseline(
    *,
    dataset_path: Path,
    model_path: Path,
    metrics_path: Path,
) -> BaselineTrainingResult:
    """
    Train the Sprint 11 TF-IDF + metadata Logistic
    Regression baseline.
    """

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}"
        )

    dataframe = pd.read_csv(
        dataset_path
    )

    dataframe = (
        _prepare_dataframe(
            dataframe
        )
    )

    _validate_training_readiness(
        dataframe
    )

    class_counts = (
        dataframe[TARGET_COLUMN]
        .value_counts()
    )

    classes = sorted(
        class_counts
        .index
        .tolist()
    )

    X = dataframe[
        [
            TEXT_COLUMN,
            *NUMERIC_COLUMNS,
            *CATEGORICAL_COLUMNS,
        ]
    ]

    y = dataframe[
        TARGET_COLUMN
    ]

    test_size = (
        _safe_test_size(
            total_rows=len(
                dataframe
            ),
            class_count=len(
                classes
            ),
        )
    )

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
        stratify=y,
    )

    pipeline = (
        _build_pipeline()
    )

    pipeline.fit(
        X_train,
        y_train,
    )

    predictions = (
        pipeline.predict(
            X_test
        )
    )

    accuracy = (
        accuracy_score(
            y_test,
            predictions,
        )
    )

    macro_precision = (
        precision_score(
            y_test,
            predictions,
            average="macro",
            zero_division=0,
        )
    )

    macro_recall = (
        recall_score(
            y_test,
            predictions,
            average="macro",
            zero_division=0,
        )
    )

    macro_f1 = (
        f1_score(
            y_test,
            predictions,
            average="macro",
            zero_division=0,
        )
    )

    report = (
        classification_report(
            y_test,
            predictions,
            labels=classes,
            output_dict=True,
            zero_division=0,
        )
    )

    matrix = (
        confusion_matrix(
            y_test,
            predictions,
            labels=classes,
        )
    )

    serious_training_ready = (
        len(dataframe) >= 50
        and class_counts.min() >= 5
    )

    model_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metrics_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = {
        "artifact_type":
            "misconceptionos-baseline-state-classifier",

        "model_version":
            MODEL_VERSION,

        "pipeline":
            pipeline,

        "classes":
            classes,

        "target_column":
            TARGET_COLUMN,

        "feature_columns": {
            "text":
                TEXT_COLUMN,

            "numeric":
                NUMERIC_COLUMNS,

            "categorical":
                CATEGORICAL_COLUMNS,
        },

        "training_metadata": {
            "total_rows":
                len(dataframe),

            "train_rows":
                len(X_train),

            "test_rows":
                len(X_test),

            "serious_training_ready":
                serious_training_ready,
        },
    }

    joblib.dump(
        artifact,
        model_path,
    )

    result = (
        BaselineTrainingResult(
            model_version=(
                MODEL_VERSION
            ),

            dataset_path=str(
                dataset_path
            ),

            total_rows=len(
                dataframe
            ),

            train_rows=len(
                X_train
            ),

            test_rows=len(
                X_test
            ),

            classes=classes,

            accuracy=float(
                accuracy
            ),

            macro_precision=float(
                macro_precision
            ),

            macro_recall=float(
                macro_recall
            ),

            macro_f1=float(
                macro_f1
            ),

            classification_report=(
                report
            ),

            confusion_matrix=(
                matrix
                .astype(int)
                .tolist()
            ),

            model_path=str(
                model_path
            ),

            metrics_path=str(
                metrics_path
            ),

            serious_training_ready=(
                serious_training_ready
            ),
        )
    )

    metrics_path.write_text(
        json.dumps(
            asdict(result),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return result


def print_result(
    result: BaselineTrainingResult,
) -> None:
    print()
    print("=" * 72)
    print(
        "SPRINT 11 BASELINE ML TRAINING"
    )
    print("=" * 72)

    print(
        f"Model version: "
        f"{result.model_version}"
    )

    print(
        f"Dataset: "
        f"{result.dataset_path}"
    )

    print(
        f"Total rows: "
        f"{result.total_rows}"
    )

    print(
        f"Train rows: "
        f"{result.train_rows}"
    )

    print(
        f"Test rows: "
        f"{result.test_rows}"
    )

    print(
        "Classes: "
        + ", ".join(
            result.classes
        )
    )

    print()
    print("Metrics")
    print("-------")

    print(
        f"Accuracy:        "
        f"{result.accuracy:.4f}"
    )

    print(
        f"Macro precision: "
        f"{result.macro_precision:.4f}"
    )

    print(
        f"Macro recall:    "
        f"{result.macro_recall:.4f}"
    )

    print(
        f"Macro F1:        "
        f"{result.macro_f1:.4f}"
    )

    print()
    print("Confusion matrix")
    print("----------------")

    print(
        "Label order: "
        + ", ".join(
            result.classes
        )
    )

    for row in (
        result.confusion_matrix
    ):
        print(
            "  "
            + " ".join(
                str(value)
                for value in row
            )
        )

    print()
    print("Artifacts")
    print("---------")

    print(
        f"Model:   "
        f"{result.model_path}"
    )

    print(
        f"Metrics: "
        f"{result.metrics_path}"
    )

    print()
    print("Interpretation")
    print("--------------")

    if (
        result.serious_training_ready
    ):
        print(
            "Dataset meets the current minimum "
            "threshold for an initial supervised "
            "baseline."
        )

    else:
        print(
            "SMOKE BASELINE ONLY."
        )

        print(
            "The current dataset does not meet "
            "the threshold for scientifically "
            "meaningful performance claims."
        )

        print(
            "Use these metrics only to verify "
            "the training and inference pipeline."
        )

        print(
            "Do not report these values as "
            "final model quality."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train the Sprint 11 TF-IDF + metadata "
            "multiclass Logistic Regression baseline."
        )
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=MODEL_PATH,
    )

    parser.add_argument(
        "--metrics",
        type=Path,
        default=METRICS_PATH,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = train_baseline(
        dataset_path=(
            args.dataset
        ),
        model_path=(
            args.model
        ),
        metrics_path=(
            args.metrics
        ),
    )

    print_result(
        result
    )


if __name__ == "__main__":
    main()