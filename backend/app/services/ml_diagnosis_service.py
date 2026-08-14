from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from app.ml.fusion import (
    FusionConfig,
    HybridFusionResult,
    RulePrediction,
    fuse_rule_and_ml,
    rule_prediction_from_mapping,
)
from app.ml.inference import (
    BaselinePrediction,
    baseline_model_available,
    predict_baseline,
)


ML_DIAGNOSIS_SERVICE_VERSION = "ml-diagnosis-service-v1.0"


STATE_TO_NEXT_ACTION: dict[str, str] = {
    "confident": "show_hint",
    "possible": "ask_diagnostic_question",
    "insufficient": "ask_clarification",
    "no_misconception": "no_action",
}


SUPPORTED_STATES = {
    "confident",
    "possible",
    "insufficient",
    "no_misconception",
}


@dataclass(
    slots=True,
    frozen=True,
)
class MLDiagnosisServiceResult:
    """
    Diagnosis-ready output produced by the Sprint 11 ML/hybrid layer.

    This result does not persist anything.

    The caller may later copy these fields into the Diagnosis model.

    Important fields:

    state
        Final state after rule + ML fusion and persistence-contract
        normalization.

    confidence
        Final confidence safe for the current Diagnosis constraints.

    primary_misconception_id
        Misconception inherited from the rule path when the final
        state requires one.

    next_action
        Existing intervention-compatible action.

    rule_score
        Existing rule score, when available.

    ml_score
        Probability assigned by the ML classifier to its predicted
        state.

    hybrid_score
        Raw weighted fusion score before persistence normalization.

    prediction_source
        "hybrid" for successful ML + rule fusion.
    """

    state: str
    confidence: float
    primary_misconception_id: str | None

    next_action: str

    decision_reason: str

    rule_score: float | None
    ml_score: float
    hybrid_score: float

    prediction_source: str

    model_version: str
    rule_model_version: str | None
    ml_model_version: str
    feature_version: str | None
    calibration_version: str | None

    rule_state: str
    ml_state: str

    rule_confidence: float
    ml_confidence: float

    agreement: bool

    service_version: str

    ml_prediction: BaselinePrediction
    fusion_result: HybridFusionResult

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "state":
                self.state,

            "confidence":
                self.confidence,

            "primary_misconception_id":
                self.primary_misconception_id,

            "next_action":
                self.next_action,

            "decision_reason":
                self.decision_reason,

            "rule_score":
                self.rule_score,

            "ml_score":
                self.ml_score,

            "hybrid_score":
                self.hybrid_score,

            "prediction_source":
                self.prediction_source,

            "model_version":
                self.model_version,

            "rule_model_version":
                self.rule_model_version,

            "ml_model_version":
                self.ml_model_version,

            "feature_version":
                self.feature_version,

            "calibration_version":
                self.calibration_version,

            "rule_state":
                self.rule_state,

            "ml_state":
                self.ml_state,

            "rule_confidence":
                self.rule_confidence,

            "ml_confidence":
                self.ml_confidence,

            "agreement":
                self.agreement,

            "service_version":
                self.service_version,

            "ml_prediction":
                self.ml_prediction.to_dict(),

            "fusion_result":
                self.fusion_result.to_dict(),
        }


@dataclass(
    slots=True,
    frozen=True,
)
class MLDiagnosisAvailability:
    """
    Runtime availability information for the ML diagnosis layer.
    """

    available: bool
    model_path: str | None
    reason: str | None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


def _normalize_optional_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    normalized = (
        str(value)
        .strip()
    )

    return (
        normalized
        or None
    )


def _normalize_state(
    value: Any,
    *,
    field_name: str,
) -> str:
    if value is None:
        raise ValueError(
            f"{field_name} is required."
        )

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    if (
        normalized
        not in SUPPORTED_STATES
    ):
        raise ValueError(
            f"Unsupported {field_name}: "
            f"{value!r}."
        )

    return normalized


def _normalize_probability(
    value: Any,
    *,
    field_name: str,
) -> float:
    if value is None:
        raise ValueError(
            f"{field_name} is required."
        )

    probability = float(
        value
    )

    if not (
        0.0
        <= probability
        <= 1.0
    ):
        raise ValueError(
            f"{field_name} must be between "
            "0 and 1."
        )

    return probability


def _extract_rule_score(
    rule: RulePrediction,
) -> float | None:
    if rule.rule_score is None:
        return None

    return float(
        rule.rule_score
    )


def _resolve_next_action(
    state: str,
) -> str:
    normalized_state = (
        _normalize_state(
            state,
            field_name="state",
        )
    )

    try:
        return (
            STATE_TO_NEXT_ACTION[
                normalized_state
            ]
        )

    except KeyError as exc:
        raise ValueError(
            "No intervention action is "
            f"configured for state "
            f"{normalized_state!r}."
        ) from exc


def build_attempt_ml_payload(
    attempt: Mapping[
        str,
        Any,
    ],
    *,
    rule_prediction: RulePrediction,
) -> dict[str, Any]:
    """
    Build the raw mapping consumed by app.ml.inference.

    The feature builder remains responsible for normalizing missing
    fields and deriving lengths/modality indicators.

    Rule outputs are included because the current baseline model was
    trained with rule-derived context features.

    IMPORTANT:
    Later research-quality ML-only evaluation should train a separate
    model that excludes these rule features.
    """

    if not isinstance(
        attempt,
        Mapping,
    ):
        raise TypeError(
            "attempt must be a mapping."
        )

    payload = dict(
        attempt
    )

    payload[
        "rule_state"
    ] = (
        rule_prediction.state
    )

    payload[
        "rule_confidence"
    ] = float(
        rule_prediction.confidence
    )

    payload[
        "rule_score"
    ] = (
        rule_prediction.rule_score
        if rule_prediction.rule_score
        is not None
        else rule_prediction.confidence
    )

    payload[
        "rule_misconception_id"
    ] = (
        rule_prediction
        .primary_misconception_id
    )

    return payload


def _build_result(
    *,
    rule_prediction: RulePrediction,
    ml_prediction: BaselinePrediction,
    fusion_result: HybridFusionResult,
) -> MLDiagnosisServiceResult:
    final_state = (
        _normalize_state(
            fusion_result.state,
            field_name="fusion state",
        )
    )

    final_confidence = (
        _normalize_probability(
            fusion_result.confidence,
            field_name=(
                "fusion confidence"
            ),
        )
    )

    next_action = (
        _resolve_next_action(
            final_state
        )
    )

    misconception_id = (
        _normalize_optional_string(
            fusion_result
            .primary_misconception_id
        )
    )

    if (
        final_state
        in {
            "confident",
            "possible",
        }
        and misconception_id
        is None
    ):
        raise ValueError(
            "Hybrid misconception state "
            "requires a misconception ID."
        )

    if (
        final_state
        in {
            "insufficient",
            "no_misconception",
        }
        and misconception_id
        is not None
    ):
        raise ValueError(
            "Hybrid non-misconception state "
            "must not contain a "
            "misconception ID."
        )

    ml_score = (
        _normalize_probability(
            ml_prediction.confidence,
            field_name=(
                "ML confidence"
            ),
        )
    )

    hybrid_score = (
        _normalize_probability(
            fusion_result
            .raw_hybrid_confidence,
            field_name=(
                "hybrid score"
            ),
        )
    )

    return (
        MLDiagnosisServiceResult(
            state=(
                final_state
            ),

            confidence=(
                final_confidence
            ),

            primary_misconception_id=(
                misconception_id
            ),

            next_action=(
                next_action
            ),

            decision_reason=(
                fusion_result
                .decision_reason
            ),

            rule_score=(
                _extract_rule_score(
                    rule_prediction
                )
            ),

            ml_score=(
                ml_score
            ),

            hybrid_score=(
                hybrid_score
            ),

            prediction_source=(
                "hybrid"
            ),

            model_version=(
                fusion_result
                .model_version
            ),

            rule_model_version=(
                rule_prediction
                .model_version
            ),

            ml_model_version=(
                ml_prediction
                .model_version
            ),

            feature_version=(
                ml_prediction
                .feature_version
            ),

            calibration_version=None,

            rule_state=(
                rule_prediction
                .state
            ),

            ml_state=(
                ml_prediction
                .predicted_state
            ),

            rule_confidence=(
                float(
                    rule_prediction
                    .confidence
                )
            ),

            ml_confidence=(
                float(
                    ml_prediction
                    .confidence
                )
            ),

            agreement=(
                fusion_result
                .agreement
            ),

            service_version=(
                ML_DIAGNOSIS_SERVICE_VERSION
            ),

            ml_prediction=(
                ml_prediction
            ),

            fusion_result=(
                fusion_result
            ),
        )
    )


def diagnose_with_ml(
    *,
    attempt: Mapping[
        str,
        Any,
    ],
    rule_prediction: RulePrediction,
    model_path: Path | str | None = None,
    fusion_config: FusionConfig | None = None,
    use_model_cache: bool = True,
) -> MLDiagnosisServiceResult:
    """
    Run the complete Sprint 11 engineering ML path:

        attempt
            +
        rule prediction
            ↓
        ML feature builder
            ↓
        persisted baseline model
            ↓
        ML state prediction
            ↓
        rule + ML fusion
            ↓
        diagnosis-ready result

    No database mutation occurs here.
    """

    ml_payload = (
        build_attempt_ml_payload(
            attempt,
            rule_prediction=(
                rule_prediction
            ),
        )
    )

    ml_prediction = (
        predict_baseline(
            ml_payload,

            model_path=(
                model_path
            ),

            use_cache=(
                use_model_cache
            ),
        )
    )

    fusion_result = (
        fuse_rule_and_ml(
            rule_prediction,
            ml_prediction,

            config=(
                fusion_config
            ),
        )
    )

    return (
        _build_result(
            rule_prediction=(
                rule_prediction
            ),

            ml_prediction=(
                ml_prediction
            ),

            fusion_result=(
                fusion_result
            ),
        )
    )


def diagnose_with_ml_from_mapping(
    *,
    attempt: Mapping[
        str,
        Any,
    ],
    rule_result: Mapping[
        str,
        Any,
    ],
    model_path: Path | str | None = None,
    fusion_config: FusionConfig | None = None,
    use_model_cache: bool = True,
) -> MLDiagnosisServiceResult:
    """
    Mapping adapter for callers that already hold the rule result as
    a dictionary.
    """

    rule_prediction = (
        rule_prediction_from_mapping(
            rule_result
        )
    )

    return diagnose_with_ml(
        attempt=attempt,

        rule_prediction=(
            rule_prediction
        ),

        model_path=(
            model_path
        ),

        fusion_config=(
            fusion_config
        ),

        use_model_cache=(
            use_model_cache
        ),
    )


def ml_diagnosis_available(
    model_path: Path | str | None = None,
) -> MLDiagnosisAvailability:
    """
    Check whether the persisted baseline artifact is available.

    This does not deserialize the model. Real inference will still
    validate the artifact before use.
    """

    available = (
        baseline_model_available(
            model_path
        )
    )

    if model_path is None:
        resolved_path = None
    else:
        resolved_path = str(
            Path(
                model_path
            )
            .expanduser()
            .resolve()
        )

    if available:
        reason = None
    else:
        reason = (
            "Baseline ML artifact is "
            "not available."
        )

    return MLDiagnosisAvailability(
        available=(
            available
        ),

        model_path=(
            resolved_path
        ),

        reason=(
            reason
        ),
    )


def diagnosis_model_fields(
    result: MLDiagnosisServiceResult,
) -> dict[str, Any]:
    """
    Return only fields intended for the Diagnosis ORM model.

    This helper is the bridge we will later use from the existing
    diagnosis persistence service.

    It deliberately excludes nested debug objects.
    """

    return {
        "state":
            result.state,

        "primary_misconception_id":
            result.primary_misconception_id,

        "confidence":
            result.confidence,

        "model_version":
            result.model_version,

        "decision_reason":
            result.decision_reason,

        "next_action":
            result.next_action,

        "rule_score":
            result.rule_score,

        "ml_score":
            result.ml_score,

        "hybrid_score":
            result.hybrid_score,

        "prediction_source":
            result.prediction_source,

        "feature_version":
            result.feature_version,

        "calibration_version":
            result.calibration_version,
    }


def rule_only_diagnosis_model_fields(
    *,
    state: str,
    confidence: float,
    primary_misconception_id: str | None,
    decision_reason: str | None,
    rule_score: float | None,
    model_version: str,
) -> dict[str, Any]:
    """
    Build explicit rule-only Diagnosis fields.

    This helper matters because Sprint 11 must preserve the existing
    rule path as a safe fallback whenever ML is disabled/unavailable.
    """

    normalized_state = (
        _normalize_state(
            state,
            field_name="state",
        )
    )

    normalized_confidence = (
        _normalize_probability(
            confidence,
            field_name="confidence",
        )
    )

    misconception_id = (
        _normalize_optional_string(
            primary_misconception_id
        )
    )

    if (
        normalized_state
        in {
            "confident",
            "possible",
        }
        and misconception_id
        is None
    ):
        raise ValueError(
            "Rule misconception state "
            "requires a misconception ID."
        )

    if (
        normalized_state
        in {
            "insufficient",
            "no_misconception",
        }
        and misconception_id
        is not None
    ):
        raise ValueError(
            "Rule non-misconception state "
            "must not contain a misconception ID."
        )

    normalized_rule_score: (
        float
        | None
    )

    if rule_score is None:
        normalized_rule_score = None
    else:
        normalized_rule_score = (
            _normalize_probability(
                rule_score,
                field_name=(
                    "rule_score"
                ),
            )
        )

    return {
        "state":
            normalized_state,

        "primary_misconception_id":
            misconception_id,

        "confidence":
            normalized_confidence,

        "model_version":
            str(
                model_version
            ).strip(),

        "decision_reason":
            _normalize_optional_string(
                decision_reason
            ),

        "next_action":
            _resolve_next_action(
                normalized_state
            ),

        "rule_score":
            normalized_rule_score,

        "ml_score":
            None,

        "hybrid_score":
            None,

        "prediction_source":
            "rule",

        "feature_version":
            None,

        "calibration_version":
            None,
    }


__all__ = [
    "ML_DIAGNOSIS_SERVICE_VERSION",
    "STATE_TO_NEXT_ACTION",
    "SUPPORTED_STATES",
    "MLDiagnosisServiceResult",
    "MLDiagnosisAvailability",
    "build_attempt_ml_payload",
    "diagnose_with_ml",
    "diagnose_with_ml_from_mapping",
    "ml_diagnosis_available",
    "diagnosis_model_fields",
    "rule_only_diagnosis_model_fields",
]