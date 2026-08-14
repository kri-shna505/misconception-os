from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.ml.inference import (
    BaselinePrediction,
    ClassProbability,
)


SUPPORTED_STATES = (
    "confident",
    "possible",
    "insufficient",
    "no_misconception",
)

MISCONCEPTION_STATES = {
    "confident",
    "possible",
}

DEFAULT_RULE_WEIGHT = 0.45
DEFAULT_ML_WEIGHT = 0.55

CONFIDENT_THRESHOLD = 0.75
POSSIBLE_THRESHOLD = 0.45

HYBRID_VERSION = "hybrid-fusion-v1.0"


@dataclass(
    slots=True,
    frozen=True,
)
class FusionConfig:
    """
    Configuration for the first Sprint 11 fusion layer.

    IMPORTANT:
    These weights are engineering defaults only.

    They must not be presented as scientifically optimized weights.
    Later evaluation should compare candidate configurations using
    teacher-reviewed validation data.
    """

    rule_weight: float = DEFAULT_RULE_WEIGHT
    ml_weight: float = DEFAULT_ML_WEIGHT

    confident_threshold: float = CONFIDENT_THRESHOLD
    possible_threshold: float = POSSIBLE_THRESHOLD

    version: str = HYBRID_VERSION

    def __post_init__(
        self,
    ) -> None:
        if not (
            0.0
            <= self.rule_weight
            <= 1.0
        ):
            raise ValueError(
                "rule_weight must be between 0 and 1."
            )

        if not (
            0.0
            <= self.ml_weight
            <= 1.0
        ):
            raise ValueError(
                "ml_weight must be between 0 and 1."
            )

        total_weight = (
            self.rule_weight
            + self.ml_weight
        )

        if total_weight <= 0.0:
            raise ValueError(
                "At least one fusion weight must be positive."
            )

        if not (
            0.0
            <= self.possible_threshold
            < self.confident_threshold
            <= 1.0
        ):
            raise ValueError(
                "Thresholds must satisfy "
                "0 <= possible < confident <= 1."
            )


@dataclass(
    slots=True,
    frozen=True,
)
class RulePrediction:
    """
    Minimal rule-engine contract consumed by the fusion layer.

    primary_misconception_id may be a UUID string, a stable code such
    as M1, or None depending on the calling service.
    """

    state: str
    confidence: float
    primary_misconception_id: str | None = None
    rule_score: float | None = None
    model_version: str | None = None

    def __post_init__(
        self,
    ) -> None:
        normalized_state = (
            self.state
            .strip()
            .lower()
        )

        if (
            normalized_state
            not in SUPPORTED_STATES
        ):
            raise ValueError(
                "Unsupported rule state: "
                f"{self.state!r}."
            )

        if not (
            0.0
            <= float(
                self.confidence
            )
            <= 1.0
        ):
            raise ValueError(
                "Rule confidence must be between 0 and 1."
            )

        if (
            self.rule_score is not None
            and not (
                0.0
                <= float(
                    self.rule_score
                )
                <= 1.0
            )
        ):
            raise ValueError(
                "rule_score must be between 0 and 1."
            )


@dataclass(
    slots=True,
    frozen=True,
)
class HybridClassScore:
    state: str
    rule_probability: float
    ml_probability: float
    hybrid_probability: float


@dataclass(
    slots=True,
    frozen=True,
)
class HybridFusionResult:
    """
    Result of combining rule and ML state evidence.

    candidate_state:
        Highest-scoring state before enforcing the existing Diagnosis
        persistence contract.

    state:
        State safe for the current Diagnosis model thresholds.

    confidence:
        Confidence safe for the current Diagnosis DB constraints.

    primary_misconception_id:
        Misconception inherited from rule evidence when the resulting
        state requires one.

    agreement:
        True when rule and ML choose the same top-level state.
    """

    candidate_state: str
    state: str

    confidence: float
    raw_hybrid_confidence: float

    primary_misconception_id: str | None

    agreement: bool

    rule_state: str
    ml_state: str

    rule_confidence: float
    ml_confidence: float

    rule_weight: float
    ml_weight: float

    scores: tuple[
        HybridClassScore,
        ...
    ]

    prediction_source: str
    model_version: str
    ml_model_version: str
    rule_model_version: str | None

    decision_reason: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "candidate_state":
                self.candidate_state,

            "state":
                self.state,

            "confidence":
                self.confidence,

            "raw_hybrid_confidence":
                self.raw_hybrid_confidence,

            "primary_misconception_id":
                self.primary_misconception_id,

            "agreement":
                self.agreement,

            "rule_state":
                self.rule_state,

            "ml_state":
                self.ml_state,

            "rule_confidence":
                self.rule_confidence,

            "ml_confidence":
                self.ml_confidence,

            "rule_weight":
                self.rule_weight,

            "ml_weight":
                self.ml_weight,

            "scores": [
                asdict(
                    score
                )
                for score
                in self.scores
            ],

            "prediction_source":
                self.prediction_source,

            "model_version":
                self.model_version,

            "ml_model_version":
                self.ml_model_version,

            "rule_model_version":
                self.rule_model_version,

            "decision_reason":
                self.decision_reason,
        }


def _normalize_probability(
    value: float,
) -> float:
    probability = float(
        value
    )

    if probability < 0.0:
        return 0.0

    if probability > 1.0:
        return 1.0

    return probability


def _normalized_weights(
    config: FusionConfig,
) -> tuple[
    float,
    float,
]:
    total = (
        config.rule_weight
        + config.ml_weight
    )

    return (
        config.rule_weight
        / total,

        config.ml_weight
        / total,
    )


def _rule_probability_distribution(
    rule: RulePrediction,
) -> dict[str, float]:
    """
    Convert the existing rule engine's state + confidence output into
    a four-state probability-like distribution.

    The rule engine currently does not expose a full distribution.
    Therefore the residual mass is distributed uniformly across the
    remaining states.

    This is an engineering bridge, not learned calibration.
    """

    state = (
        rule.state
        .strip()
        .lower()
    )

    confidence = (
        _normalize_probability(
            rule.confidence
        )
    )

    remaining_states = [
        candidate
        for candidate
        in SUPPORTED_STATES
        if candidate != state
    ]

    residual = max(
        0.0,
        1.0 - confidence,
    )

    residual_each = (
        residual
        / len(
            remaining_states
        )
    )

    result = {
        candidate:
            residual_each
        for candidate
        in remaining_states
    }

    result[state] = confidence

    return result


def _ml_probability_distribution(
    prediction: BaselinePrediction,
) -> dict[str, float]:
    distribution = {
        state: 0.0
        for state
        in SUPPORTED_STATES
    }

    for item in (
        prediction.probabilities
    ):
        label = (
            item.label
            .strip()
            .lower()
        )

        if (
            label
            not in distribution
        ):
            continue

        distribution[
            label
        ] = (
            _normalize_probability(
                item.probability
            )
        )

    total = sum(
        distribution.values()
    )

    if total <= 0.0:
        raise ValueError(
            "ML prediction contains no usable "
            "probability mass."
        )

    return {
        state:
            value / total
        for (
            state,
            value,
        )
        in distribution.items()
    }


def _calculate_hybrid_scores(
    *,
    rule_distribution: Mapping[
        str,
        float,
    ],
    ml_distribution: Mapping[
        str,
        float,
    ],
    config: FusionConfig,
) -> tuple[
    HybridClassScore,
    ...
]:
    rule_weight, ml_weight = (
        _normalized_weights(
            config
        )
    )

    scores: list[
        HybridClassScore
    ] = []

    for state in SUPPORTED_STATES:
        rule_probability = (
            _normalize_probability(
                rule_distribution.get(
                    state,
                    0.0,
                )
            )
        )

        ml_probability = (
            _normalize_probability(
                ml_distribution.get(
                    state,
                    0.0,
                )
            )
        )

        hybrid_probability = (
            rule_weight
            * rule_probability
            + ml_weight
            * ml_probability
        )

        scores.append(
            HybridClassScore(
                state=state,

                rule_probability=(
                    rule_probability
                ),

                ml_probability=(
                    ml_probability
                ),

                hybrid_probability=(
                    hybrid_probability
                ),
            )
        )

    return tuple(
        sorted(
            scores,
            key=lambda item: (
                item.hybrid_probability
            ),
            reverse=True,
        )
    )


def _safe_possible_confidence(
    confidence: float,
    config: FusionConfig,
) -> float:
    """
    Keep possible-state confidence inside the existing Diagnosis
    constraint:

        >= possible_threshold
        < confident_threshold
    """

    lower = (
        config.possible_threshold
    )

    upper = (
        config.confident_threshold
        - 0.000001
    )

    return min(
        max(
            confidence,
            lower,
        ),
        upper,
    )


def _safe_insufficient_confidence(
    confidence: float,
    config: FusionConfig,
) -> float:
    return min(
        max(
            confidence,
            0.0,
        ),
        config.possible_threshold
        - 0.000001,
    )


def _resolve_persistable_state(
    *,
    candidate_state: str,
    hybrid_confidence: float,
    misconception_id: str | None,
    config: FusionConfig,
) -> tuple[
    str,
    float,
    str | None,
]:
    """
    Convert the raw fusion winner into a result compatible with the
    current Diagnosis database constraints.

    Existing contract:

    confident:
        confidence >= 0.75
        misconception required

    possible:
        0.45 <= confidence < 0.75
        misconception required

    insufficient:
        confidence < 0.45
        misconception must be null

    no_misconception:
        confidence >= 0.75
        misconception must be null
    """

    candidate = (
        candidate_state
        .strip()
        .lower()
    )

    confidence = (
        _normalize_probability(
            hybrid_confidence
        )
    )

    if candidate == "no_misconception":
        if (
            confidence
            >= config.confident_threshold
        ):
            return (
                "no_misconception",
                confidence,
                None,
            )

        return (
            "insufficient",
            _safe_insufficient_confidence(
                1.0 - confidence,
                config,
            ),
            None,
        )

    if candidate == "insufficient":
        return (
            "insufficient",
            _safe_insufficient_confidence(
                confidence,
                config,
            ),
            None,
        )

    if candidate in MISCONCEPTION_STATES:
        if not misconception_id:
            return (
                "insufficient",
                _safe_insufficient_confidence(
                    min(
                        confidence,
                        config.possible_threshold
                        - 0.000001,
                    ),
                    config,
                ),
                None,
            )

        if (
            confidence
            >= config.confident_threshold
        ):
            return (
                "confident",
                confidence,
                misconception_id,
            )

        if (
            confidence
            >= config.possible_threshold
        ):
            return (
                "possible",
                _safe_possible_confidence(
                    confidence,
                    config,
                ),
                misconception_id,
            )

        return (
            "insufficient",
            _safe_insufficient_confidence(
                confidence,
                config,
            ),
            None,
        )

    raise ValueError(
        "Unsupported candidate state: "
        f"{candidate_state!r}."
    )


def _build_decision_reason(
    *,
    rule: RulePrediction,
    ml: BaselinePrediction,
    candidate_state: str,
    final_state: str,
    agreement: bool,
    raw_confidence: float,
) -> str:
    if agreement:
        prefix = (
            "Rule and ML predictions agree"
        )
    else:
        prefix = (
            "Rule and ML predictions disagree"
        )

    reason = (
        f"{prefix}: "
        f"rule={rule.state} "
        f"({rule.confidence:.3f}), "
        f"ml={ml.predicted_state} "
        f"({ml.confidence:.3f}). "
        f"Weighted fusion selected "
        f"{candidate_state} "
        f"with raw score "
        f"{raw_confidence:.3f}."
    )

    if (
        final_state
        != candidate_state
    ):
        reason += (
            " The candidate was normalized to "
            f"{final_state} to satisfy the current "
            "Diagnosis state/confidence persistence contract."
        )

    return reason


def fuse_rule_and_ml(
    rule: RulePrediction,
    ml: BaselinePrediction,
    *,
    config: FusionConfig | None = None,
) -> HybridFusionResult:
    """
    Fuse one rule-engine result with one ML prediction.

    This is deliberately deterministic.

    No database access occurs here.
    No intervention is selected here.
    No teacher-review state is used here.
    """

    active_config = (
        config
        or FusionConfig()
    )

    rule_distribution = (
        _rule_probability_distribution(
            rule
        )
    )

    ml_distribution = (
        _ml_probability_distribution(
            ml
        )
    )

    scores = (
        _calculate_hybrid_scores(
            rule_distribution=(
                rule_distribution
            ),

            ml_distribution=(
                ml_distribution
            ),

            config=(
                active_config
            ),
        )
    )

    if not scores:
        raise RuntimeError(
            "Fusion produced no state scores."
        )

    winner = scores[0]

    candidate_state = (
        winner.state
    )

    raw_hybrid_confidence = (
        _normalize_probability(
            winner.hybrid_probability
        )
    )

    rule_state = (
        rule.state
        .strip()
        .lower()
    )

    ml_state = (
        ml.predicted_state
        .strip()
        .lower()
    )

    agreement = (
        rule_state
        == ml_state
    )

    misconception_id = (
        rule.primary_misconception_id
    )

    (
        final_state,
        final_confidence,
        final_misconception_id,
    ) = _resolve_persistable_state(
        candidate_state=(
            candidate_state
        ),

        hybrid_confidence=(
            raw_hybrid_confidence
        ),

        misconception_id=(
            misconception_id
        ),

        config=(
            active_config
        ),
    )

    rule_weight, ml_weight = (
        _normalized_weights(
            active_config
        )
    )

    decision_reason = (
        _build_decision_reason(
            rule=rule,
            ml=ml,

            candidate_state=(
                candidate_state
            ),

            final_state=(
                final_state
            ),

            agreement=(
                agreement
            ),

            raw_confidence=(
                raw_hybrid_confidence
            ),
        )
    )

    return HybridFusionResult(
        candidate_state=(
            candidate_state
        ),

        state=(
            final_state
        ),

        confidence=(
            final_confidence
        ),

        raw_hybrid_confidence=(
            raw_hybrid_confidence
        ),

        primary_misconception_id=(
            final_misconception_id
        ),

        agreement=(
            agreement
        ),

        rule_state=(
            rule_state
        ),

        ml_state=(
            ml_state
        ),

        rule_confidence=(
            float(
                rule.confidence
            )
        ),

        ml_confidence=(
            float(
                ml.confidence
            )
        ),

        rule_weight=(
            rule_weight
        ),

        ml_weight=(
            ml_weight
        ),

        scores=(
            scores
        ),

        prediction_source=(
            "hybrid"
        ),

        model_version=(
            active_config.version
        ),

        ml_model_version=(
            ml.model_version
        ),

        rule_model_version=(
            rule.model_version
        ),

        decision_reason=(
            decision_reason
        ),
    )


def rule_prediction_from_mapping(
    payload: Mapping[
        str,
        Any,
    ],
) -> RulePrediction:
    """
    Convenience adapter for service-layer dictionaries.
    """

    state = str(
        payload.get(
            "state",
            "",
        )
    ).strip()

    if not state:
        raise ValueError(
            "Rule prediction state is required."
        )

    confidence_value = (
        payload.get(
            "confidence"
        )
    )

    if confidence_value is None:
        raise ValueError(
            "Rule prediction confidence is required."
        )

    misconception_value = (
        payload.get(
            "primary_misconception_id"
        )
    )

    if misconception_value is None:
        misconception_id = None
    else:
        misconception_id = (
            str(
                misconception_value
            )
            .strip()
            or None
        )

    rule_score_value = (
        payload.get(
            "rule_score"
        )
    )

    rule_score = (
        None
        if rule_score_value is None
        else float(
            rule_score_value
        )
    )

    model_version_value = (
        payload.get(
            "model_version"
        )
    )

    model_version = (
        None
        if model_version_value is None
        else (
            str(
                model_version_value
            )
            .strip()
            or None
        )
    )

    return RulePrediction(
        state=state,

        confidence=float(
            confidence_value
        ),

        primary_misconception_id=(
            misconception_id
        ),

        rule_score=(
            rule_score
        ),

        model_version=(
            model_version
        ),
    )


def fuse_rule_mapping_and_ml(
    rule_payload: Mapping[
        str,
        Any,
    ],
    ml: BaselinePrediction,
    *,
    config: FusionConfig | None = None,
) -> HybridFusionResult:
    return fuse_rule_and_ml(
        rule_prediction_from_mapping(
            rule_payload
        ),

        ml,

        config=config,
    )


__all__ = [
    "SUPPORTED_STATES",
    "MISCONCEPTION_STATES",
    "DEFAULT_RULE_WEIGHT",
    "DEFAULT_ML_WEIGHT",
    "CONFIDENT_THRESHOLD",
    "POSSIBLE_THRESHOLD",
    "HYBRID_VERSION",
    "FusionConfig",
    "RulePrediction",
    "HybridClassScore",
    "HybridFusionResult",
    "fuse_rule_and_ml",
    "rule_prediction_from_mapping",
    "fuse_rule_mapping_and_ml",
]