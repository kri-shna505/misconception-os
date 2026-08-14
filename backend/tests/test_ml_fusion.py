from __future__ import annotations

from typing import Any

import pytest

from app.ml.fusion import (
    CONFIDENT_THRESHOLD,
    DEFAULT_ML_WEIGHT,
    DEFAULT_RULE_WEIGHT,
    HYBRID_VERSION,
    POSSIBLE_THRESHOLD,
    FusionConfig,
    HybridFusionResult,
    RulePrediction,
    fuse_rule_and_ml,
    fuse_rule_mapping_and_ml,
    rule_prediction_from_mapping,
)
from app.ml.inference import (
    BaselinePrediction,
    ClassProbability,
)


def _ml_prediction(
    *,
    predicted_state: str,
    probabilities: dict[str, float],
    confidence: float | None = None,
    model_version: str = "baseline-logreg-test-v1",
) -> BaselinePrediction:
    ordered = tuple(
        ClassProbability(
            label=label,
            probability=value,
        )
        for label, value in sorted(
            probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    if confidence is None:
        confidence = probabilities[
            predicted_state
        ]

    return BaselinePrediction(
        predicted_state=predicted_state,
        confidence=confidence,
        probabilities=ordered,
        model_version=model_version,
        feature_version="features-test-v1",
        prediction_source="ml",
    )


def _confident_rule(
    *,
    confidence: float = 0.92,
    misconception_id: str | None = "M1",
) -> RulePrediction:
    return RulePrediction(
        state="confident",
        confidence=confidence,
        primary_misconception_id=misconception_id,
        rule_score=confidence,
        model_version="rule-v1.9",
    )


def _possible_rule(
    *,
    confidence: float = 0.63,
    misconception_id: str | None = "M1",
) -> RulePrediction:
    return RulePrediction(
        state="possible",
        confidence=confidence,
        primary_misconception_id=misconception_id,
        rule_score=confidence,
        model_version="rule-v1.9",
    )


def _insufficient_rule(
    *,
    confidence: float = 0.25,
) -> RulePrediction:
    return RulePrediction(
        state="insufficient",
        confidence=confidence,
        primary_misconception_id=None,
        rule_score=confidence,
        model_version="rule-v1.9",
    )


def _no_misconception_rule(
    *,
    confidence: float = 0.95,
) -> RulePrediction:
    return RulePrediction(
        state="no_misconception",
        confidence=confidence,
        primary_misconception_id=None,
        rule_score=confidence,
        model_version="rule-v1.9",
    )


def test_default_fusion_config_values() -> None:
    config = FusionConfig()

    assert config.rule_weight == DEFAULT_RULE_WEIGHT
    assert config.ml_weight == DEFAULT_ML_WEIGHT
    assert config.confident_threshold == CONFIDENT_THRESHOLD
    assert config.possible_threshold == POSSIBLE_THRESHOLD
    assert config.version == HYBRID_VERSION


@pytest.mark.parametrize(
    "rule_weight, ml_weight",
    [
        (-0.1, 1.0),
        (1.1, 0.0),
        (0.0, -0.1),
        (0.0, 1.1),
    ],
)
def test_fusion_config_rejects_invalid_weights(
    rule_weight: float,
    ml_weight: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="weight",
    ):
        FusionConfig(
            rule_weight=rule_weight,
            ml_weight=ml_weight,
        )


def test_fusion_config_requires_positive_total_weight() -> None:
    with pytest.raises(
        ValueError,
        match="At least one fusion weight",
    ):
        FusionConfig(
            rule_weight=0.0,
            ml_weight=0.0,
        )


@pytest.mark.parametrize(
    "possible_threshold, confident_threshold",
    [
        (0.8, 0.7),
        (0.75, 0.75),
        (-0.1, 0.75),
        (0.45, 1.1),
    ],
)
def test_fusion_config_rejects_invalid_thresholds(
    possible_threshold: float,
    confident_threshold: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Thresholds",
    ):
        FusionConfig(
            possible_threshold=possible_threshold,
            confident_threshold=confident_threshold,
        )


@pytest.mark.parametrize(
    "state",
    [
        "unknown",
        "",
        "correct",
    ],
)
def test_rule_prediction_rejects_invalid_state(
    state: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported rule state",
    ):
        RulePrediction(
            state=state,
            confidence=0.5,
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -0.01,
        1.01,
    ],
)
def test_rule_prediction_rejects_invalid_confidence(
    confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Rule confidence",
    ):
        RulePrediction(
            state="possible",
            confidence=confidence,
            primary_misconception_id="M1",
        )


@pytest.mark.parametrize(
    "rule_score",
    [
        -0.01,
        1.01,
    ],
)
def test_rule_prediction_rejects_invalid_rule_score(
    rule_score: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="rule_score",
    ):
        RulePrediction(
            state="possible",
            confidence=0.6,
            primary_misconception_id="M1",
            rule_score=rule_score,
        )


def test_rule_and_ml_confident_agreement_returns_hybrid_confident() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.90,
            "possible": 0.05,
            "insufficient": 0.03,
            "no_misconception": 0.02,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert isinstance(
        result,
        HybridFusionResult,
    )

    assert result.agreement is True
    assert result.candidate_state == "confident"
    assert result.state == "confident"
    assert result.primary_misconception_id == "M1"
    assert result.confidence >= CONFIDENT_THRESHOLD
    assert result.prediction_source == "hybrid"
    assert result.model_version == HYBRID_VERSION
    assert result.rule_model_version == "rule-v1.9"
    assert result.ml_model_version == "baseline-logreg-test-v1"


def test_rule_and_ml_possible_agreement_returns_possible() -> None:
    rule = _possible_rule(
        confidence=0.62
    )

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.66,
            "insufficient": 0.14,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.agreement is True
    assert result.candidate_state == "possible"
    assert result.state == "possible"

    assert (
        POSSIBLE_THRESHOLD
        <= result.confidence
        < CONFIDENT_THRESHOLD
    )

    assert result.primary_misconception_id == "M1"


def test_rule_and_ml_no_misconception_agreement_returns_no_misconception() -> None:
    rule = _no_misconception_rule()

    ml = _ml_prediction(
        predicted_state="no_misconception",
        probabilities={
            "confident": 0.02,
            "possible": 0.02,
            "insufficient": 0.01,
            "no_misconception": 0.95,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.agreement is True
    assert result.candidate_state == "no_misconception"
    assert result.state == "no_misconception"
    assert result.primary_misconception_id is None
    assert result.confidence >= CONFIDENT_THRESHOLD


def test_rule_and_ml_insufficient_agreement_returns_insufficient() -> None:
    rule = _insufficient_rule(
        confidence=0.30
    )

    ml = _ml_prediction(
        predicted_state="insufficient",
        probabilities={
            "confident": 0.08,
            "possible": 0.10,
            "insufficient": 0.76,
            "no_misconception": 0.06,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.agreement is True
    assert result.candidate_state == "insufficient"
    assert result.state == "insufficient"
    assert result.primary_misconception_id is None

    assert (
        result.confidence
        < POSSIBLE_THRESHOLD
    )


def test_rule_ml_disagreement_is_reported() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="no_misconception",
        probabilities={
            "confident": 0.05,
            "possible": 0.05,
            "insufficient": 0.05,
            "no_misconception": 0.85,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.agreement is False
    assert result.rule_state == "confident"
    assert result.ml_state == "no_misconception"

    assert (
        "disagree"
        in result.decision_reason.lower()
    )


def test_ml_dominant_no_misconception_can_win_disagreement() -> None:
    rule = RulePrediction(
        state="possible",
        confidence=0.46,
        primary_misconception_id="M1",
        model_version="rule-v1.9",
    )

    ml = _ml_prediction(
        predicted_state="no_misconception",
        probabilities={
            "confident": 0.01,
            "possible": 0.02,
            "insufficient": 0.02,
            "no_misconception": 0.95,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
        config=FusionConfig(
            rule_weight=0.20,
            ml_weight=0.80,
        ),
    )

    assert result.candidate_state == "no_misconception"


def test_rule_dominant_confident_can_win_disagreement() -> None:
    rule = _confident_rule(
        confidence=0.98
    )

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.20,
            "possible": 0.60,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
        config=FusionConfig(
            rule_weight=0.80,
            ml_weight=0.20,
        ),
    )

    assert result.candidate_state == "confident"
    assert result.primary_misconception_id == "M1"


def test_missing_misconception_id_prevents_confident_persistence() -> None:
    rule = _confident_rule(
        misconception_id=None
    )

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.95,
            "possible": 0.02,
            "insufficient": 0.02,
            "no_misconception": 0.01,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.candidate_state == "confident"
    assert result.state == "insufficient"
    assert result.primary_misconception_id is None
    assert result.confidence < POSSIBLE_THRESHOLD


def test_missing_misconception_id_prevents_possible_persistence() -> None:
    rule = _possible_rule(
        misconception_id=None
    )

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.70,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.candidate_state == "possible"
    assert result.state == "insufficient"
    assert result.primary_misconception_id is None


def test_low_confidence_misconception_candidate_becomes_insufficient() -> None:
    rule = RulePrediction(
        state="possible",
        confidence=0.46,
        primary_misconception_id="M1",
    )

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.40,
            "insufficient": 0.30,
            "no_misconception": 0.20,
        },
        confidence=0.40,
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
        config=FusionConfig(
            rule_weight=0.10,
            ml_weight=0.90,
        ),
    )

    if (
        result.candidate_state
        in {
            "confident",
            "possible",
        }
        and result.raw_hybrid_confidence
        < POSSIBLE_THRESHOLD
    ):
        assert result.state == "insufficient"


def test_no_misconception_candidate_below_threshold_is_not_persisted_as_verified() -> None:
    rule = RulePrediction(
        state="no_misconception",
        confidence=0.60,
        primary_misconception_id=None,
    )

    ml = _ml_prediction(
        predicted_state="no_misconception",
        probabilities={
            "confident": 0.10,
            "possible": 0.10,
            "insufficient": 0.10,
            "no_misconception": 0.70,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert result.candidate_state == "no_misconception"

    assert result.state in {
        "no_misconception",
        "insufficient",
    }

    if (
        result.raw_hybrid_confidence
        < CONFIDENT_THRESHOLD
    ):
        assert result.state == "insufficient"


def test_scores_include_all_supported_states() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.80,
            "possible": 0.10,
            "insufficient": 0.05,
            "no_misconception": 0.05,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    states = {
        item.state
        for item in result.scores
    }

    assert states == {
        "confident",
        "possible",
        "insufficient",
        "no_misconception",
    }


def test_hybrid_scores_are_sorted_descending() -> None:
    rule = _possible_rule()

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.70,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    values = [
        item.hybrid_probability
        for item
        in result.scores
    ]

    assert values == sorted(
        values,
        reverse=True,
    )


def test_each_hybrid_score_is_valid_probability() -> None:
    rule = _possible_rule()

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.70,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    for score in result.scores:
        assert (
            0.0
            <= score.rule_probability
            <= 1.0
        )

        assert (
            0.0
            <= score.ml_probability
            <= 1.0
        )

        assert (
            0.0
            <= score.hybrid_probability
            <= 1.0
        )


def test_normalized_weights_sum_to_one() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.80,
            "possible": 0.10,
            "insufficient": 0.05,
            "no_misconception": 0.05,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
        config=FusionConfig(
            rule_weight=2.0 / 3.0,
            ml_weight=1.0 / 3.0,
        ),
    )

    assert (
        result.rule_weight
        + result.ml_weight
    ) == pytest.approx(
        1.0,
        abs=1e-12,
    )


def test_custom_weight_ratio_is_preserved_after_normalization() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.80,
            "possible": 0.10,
            "insufficient": 0.05,
            "no_misconception": 0.05,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
        config=FusionConfig(
            rule_weight=0.25,
            ml_weight=0.75,
        ),
    )

    assert (
        result.rule_weight
        == pytest.approx(
            0.25
        )
    )

    assert (
        result.ml_weight
        == pytest.approx(
            0.75
        )
    )


def test_ml_distribution_is_normalized_when_probabilities_do_not_sum_exactly_to_one() -> None:
    rule = _possible_rule()

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.60,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    ml_total = sum(
        item.ml_probability
        for item in result.scores
    )

    assert ml_total == pytest.approx(
        1.0,
        abs=1e-12,
    )


def test_unknown_ml_probability_labels_are_ignored() -> None:
    rule = _possible_rule()

    ml = BaselinePrediction(
        predicted_state="possible",
        confidence=0.60,
        probabilities=(
            ClassProbability(
                label="possible",
                probability=0.60,
            ),
            ClassProbability(
                label="confident",
                probability=0.10,
            ),
            ClassProbability(
                label="insufficient",
                probability=0.10,
            ),
            ClassProbability(
                label="no_misconception",
                probability=0.10,
            ),
            ClassProbability(
                label="unsupported_state",
                probability=0.10,
            ),
        ),
        model_version="baseline-logreg-test-v1",
        feature_version="features-test-v1",
        prediction_source="ml",
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert len(
        result.scores
    ) == 4


def test_ml_prediction_with_no_supported_probability_mass_fails() -> None:
    rule = _possible_rule()

    ml = BaselinePrediction(
        predicted_state="possible",
        confidence=1.0,
        probabilities=(
            ClassProbability(
                label="unsupported",
                probability=1.0,
            ),
        ),
        model_version="baseline-logreg-test-v1",
        feature_version="features-test-v1",
        prediction_source="ml",
    )

    with pytest.raises(
        ValueError,
        match="no usable probability mass",
    ):
        fuse_rule_and_ml(
            rule,
            ml,
        )


def test_fusion_is_deterministic() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.88,
            "possible": 0.06,
            "insufficient": 0.03,
            "no_misconception": 0.03,
        },
    )

    first = fuse_rule_and_ml(
        rule,
        ml,
    )

    second = fuse_rule_and_ml(
        rule,
        ml,
    )

    assert first == second


def test_decision_reason_contains_rule_and_ml_states() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.20,
            "possible": 0.60,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    reason = (
        result.decision_reason
        .lower()
    )

    assert "rule=confident" in reason
    assert "ml=possible" in reason
    assert "weighted fusion" in reason


def test_result_to_dict_returns_serializable_contract() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.90,
            "possible": 0.05,
            "insufficient": 0.03,
            "no_misconception": 0.02,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    payload = result.to_dict()

    assert isinstance(
        payload,
        dict,
    )

    assert payload[
        "prediction_source"
    ] == "hybrid"

    assert payload[
        "rule_state"
    ] == "confident"

    assert payload[
        "ml_state"
    ] == "confident"

    assert isinstance(
        payload[
            "scores"
        ],
        list,
    )

    assert len(
        payload[
            "scores"
        ]
    ) == 4


def test_rule_prediction_from_mapping_builds_contract() -> None:
    payload = {
        "state":
            "confident",

        "confidence":
            0.92,

        "primary_misconception_id":
            "M1",

        "rule_score":
            0.95,

        "model_version":
            "rule-v1.9",
    }

    result = (
        rule_prediction_from_mapping(
            payload
        )
    )

    assert isinstance(
        result,
        RulePrediction,
    )

    assert result.state == "confident"
    assert result.confidence == pytest.approx(
        0.92
    )
    assert result.primary_misconception_id == "M1"
    assert result.rule_score == pytest.approx(
        0.95
    )
    assert result.model_version == "rule-v1.9"


def test_rule_prediction_from_mapping_requires_state() -> None:
    with pytest.raises(
        ValueError,
        match="state is required",
    ):
        rule_prediction_from_mapping(
            {
                "confidence": 0.6,
            }
        )


def test_rule_prediction_from_mapping_requires_confidence() -> None:
    with pytest.raises(
        ValueError,
        match="confidence is required",
    ):
        rule_prediction_from_mapping(
            {
                "state": "possible",
            }
        )


def test_fuse_rule_mapping_and_ml_matches_direct_fusion() -> None:
    payload: dict[str, Any] = {
        "state":
            "possible",

        "confidence":
            0.62,

        "primary_misconception_id":
            "M1",

        "rule_score":
            0.64,

        "model_version":
            "rule-v1.9",
    }

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.10,
            "possible": 0.70,
            "insufficient": 0.10,
            "no_misconception": 0.10,
        },
    )

    from_mapping = (
        fuse_rule_mapping_and_ml(
            payload,
            ml,
        )
    )

    direct = fuse_rule_and_ml(
        rule_prediction_from_mapping(
            payload
        ),
        ml,
    )

    assert from_mapping == direct


def test_confident_result_satisfies_diagnosis_contract() -> None:
    rule = _confident_rule()

    ml = _ml_prediction(
        predicted_state="confident",
        probabilities={
            "confident": 0.95,
            "possible": 0.02,
            "insufficient": 0.02,
            "no_misconception": 0.01,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    if result.state == "confident":
        assert (
            result.confidence
            >= CONFIDENT_THRESHOLD
        )

        assert (
            result.primary_misconception_id
            is not None
        )


def test_possible_result_satisfies_diagnosis_contract() -> None:
    rule = _possible_rule(
        confidence=0.60
    )

    ml = _ml_prediction(
        predicted_state="possible",
        probabilities={
            "confident": 0.08,
            "possible": 0.64,
            "insufficient": 0.16,
            "no_misconception": 0.12,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    if result.state == "possible":
        assert (
            POSSIBLE_THRESHOLD
            <= result.confidence
            < CONFIDENT_THRESHOLD
        )

        assert (
            result.primary_misconception_id
            is not None
        )


def test_insufficient_result_satisfies_diagnosis_contract() -> None:
    rule = _insufficient_rule()

    ml = _ml_prediction(
        predicted_state="insufficient",
        probabilities={
            "confident": 0.05,
            "possible": 0.05,
            "insufficient": 0.85,
            "no_misconception": 0.05,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    if result.state == "insufficient":
        assert (
            result.confidence
            < POSSIBLE_THRESHOLD
        )

        assert (
            result.primary_misconception_id
            is None
        )


def test_no_misconception_result_satisfies_diagnosis_contract() -> None:
    rule = _no_misconception_rule()

    ml = _ml_prediction(
        predicted_state="no_misconception",
        probabilities={
            "confident": 0.01,
            "possible": 0.01,
            "insufficient": 0.01,
            "no_misconception": 0.97,
        },
    )

    result = fuse_rule_and_ml(
        rule,
        ml,
    )

    if result.state == "no_misconception":
        assert (
            result.confidence
            >= CONFIDENT_THRESHOLD
        )

        assert (
            result.primary_misconception_id
            is None
        )