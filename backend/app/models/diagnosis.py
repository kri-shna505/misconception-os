from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Diagnosis(Base):
    """
    Stores one structured diagnosis generated for a student attempt.

    Core diagnosis fields:
    - diagnostic state;
    - selected misconception, when applicable;
    - final confidence score;
    - model/runtime version;
    - recommended intervention;
    - human-readable decision reason.

    Sprint 9 intervention support:
    - confident -> progressive hints;
    - possible -> diagnostic question;
    - insufficient -> clarification / targeted question;
    - no_misconception -> no intervention.

    Sprint 11 AI/ML support:
    - rule_score stores the deterministic rule-engine score.
    - ml_score stores the standalone ML model probability/score.
    - hybrid_score stores the rule + ML fusion score.
    - prediction_source identifies whether the final diagnosis came from
      the rule engine, ML-only inference, or the hybrid decision layer.
    - feature_version identifies the feature-building contract used by ML.
    - calibration_version identifies the calibration artifact or strategy
      used when producing the final confidence value.

    ``confidence`` remains the canonical confidence exposed to the rest of
    the application. For hybrid diagnoses it should represent the final
    calibrated confidence rather than an uncalibrated raw model probability.

    ``llm_score`` is retained for backwards compatibility and possible future
    experimentation, but Sprint 11 does not require an LLM to produce a
    diagnosis.

    Only one diagnosis may exist for a given attempt and model_version.
    Different rule, ML, or hybrid versions may therefore coexist for the same
    attempt for evaluation and comparison.
    """

    __tablename__ = "diagnoses"

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "model_version",
            name="uq_diagnoses_attempt_model_version",
        ),

        Index(
            "ix_diagnoses_state_created_at",
            "state",
            "created_at",
        ),
        Index(
            "ix_diagnoses_misconception_created_at",
            "primary_misconception_id",
            "created_at",
        ),
        Index(
            "ix_diagnoses_model_version_created_at",
            "model_version",
            "created_at",
        ),
        Index(
            "ix_diagnoses_next_action_created_at",
            "next_action",
            "created_at",
        ),
        Index(
            "ix_diagnoses_attempt_created_at",
            "attempt_id",
            "created_at",
        ),
        Index(
            "ix_diagnoses_attempt_state",
            "attempt_id",
            "state",
        ),
        Index(
            "ix_diagnoses_state_next_action",
            "state",
            "next_action",
        ),

        # Sprint 11 indexes.
        Index(
            "ix_diagnoses_prediction_source_created_at",
            "prediction_source",
            "created_at",
        ),
        Index(
            "ix_diagnoses_feature_version_created_at",
            "feature_version",
            "created_at",
        ),
        Index(
            "ix_diagnoses_calibration_version_created_at",
            "calibration_version",
            "created_at",
        ),

        CheckConstraint(
            (
                "state IN ("
                "'confident', "
                "'possible', "
                "'insufficient', "
                "'no_misconception'"
                ")"
            ),
            name="ck_diagnoses_valid_state",
        ),

        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_diagnoses_confidence_range",
        ),

        CheckConstraint(
            (
                "rule_score IS NULL "
                "OR (rule_score >= 0.0 AND rule_score <= 1.0)"
            ),
            name="ck_diagnoses_rule_score_range",
        ),

        CheckConstraint(
            (
                "ml_score IS NULL "
                "OR (ml_score >= 0.0 AND ml_score <= 1.0)"
            ),
            name="ck_diagnoses_ml_score_range",
        ),

        CheckConstraint(
            (
                "hybrid_score IS NULL "
                "OR (hybrid_score >= 0.0 AND hybrid_score <= 1.0)"
            ),
            name="ck_diagnoses_hybrid_score_range",
        ),

        CheckConstraint(
            (
                "llm_score IS NULL "
                "OR (llm_score >= 0.0 AND llm_score <= 1.0)"
            ),
            name="ck_diagnoses_llm_score_range",
        ),

        CheckConstraint(
            (
                "prediction_source IN ("
                "'rule', "
                "'ml', "
                "'hybrid'"
                ")"
            ),
            name="ck_diagnoses_valid_prediction_source",
        ),

        CheckConstraint(
            (
                "next_action IN ("
                "'show_hint', "
                "'ask_diagnostic_question', "
                "'ask_clarification', "
                "'no_action'"
                ")"
            ),
            name="ck_diagnoses_valid_next_action",
        ),

        CheckConstraint(
            (
                "("
                "state IN ('confident', 'possible') "
                "AND primary_misconception_id IS NOT NULL"
                ") "
                "OR "
                "("
                "state IN ('insufficient', 'no_misconception') "
                "AND primary_misconception_id IS NULL"
                ")"
            ),
            name="ck_diagnoses_state_misconception_consistency",
        ),

        CheckConstraint(
            (
                "("
                "state = 'confident' "
                "AND confidence >= 0.75"
                ") "
                "OR "
                "("
                "state = 'possible' "
                "AND confidence >= 0.45 "
                "AND confidence < 0.75"
                ") "
                "OR "
                "("
                "state = 'insufficient' "
                "AND confidence < 0.45"
                ") "
                "OR "
                "("
                "state = 'no_misconception' "
                "AND confidence >= 0.75"
                ")"
            ),
            name="ck_diagnoses_state_confidence_consistency",
        ),

        CheckConstraint(
            (
                "("
                "state = 'confident' "
                "AND next_action = 'show_hint'"
                ") "
                "OR "
                "("
                "state = 'possible' "
                "AND next_action = 'ask_diagnostic_question'"
                ") "
                "OR "
                "("
                "state = 'insufficient' "
                "AND next_action IN ("
                "'ask_clarification', "
                "'ask_diagnostic_question'"
                ")"
                ") "
                "OR "
                "("
                "state = 'no_misconception' "
                "AND next_action = 'no_action'"
                ")"
            ),
            name="ck_diagnoses_state_next_action_consistency",
        ),

        # Sprint 11 consistency rules.
        CheckConstraint(
            (
                "prediction_source <> 'ml' "
                "OR ml_score IS NOT NULL"
            ),
            name="ck_diagnoses_ml_source_requires_ml_score",
        ),

        CheckConstraint(
            (
                "prediction_source <> 'hybrid' "
                "OR hybrid_score IS NOT NULL"
            ),
            name="ck_diagnoses_hybrid_source_requires_hybrid_score",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "attempts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    state = Column(
        String(30),
        nullable=False,
        index=True,
    )

    primary_misconception_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "misconceptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0",
    )

    model_version = Column(
        String(80),
        nullable=False,
        default="rule-v1.9",
        server_default="rule-v1.9",
        index=True,
    )

    decision_reason = Column(
        Text,
        nullable=True,
    )

    next_action = Column(
        String(50),
        nullable=False,
        default="no_action",
        server_default="no_action",
        index=True,
    )

    # ------------------------------------------------------------------
    # Component scores
    # ------------------------------------------------------------------

    rule_score = Column(
        Float,
        nullable=True,
    )

    # Sprint 11:
    # Probability/score produced by the standalone ML classifier.
    ml_score = Column(
        Float,
        nullable=True,
    )

    # Sprint 11:
    # Score produced after rule + ML fusion.
    hybrid_score = Column(
        Float,
        nullable=True,
    )

    # Kept for backwards compatibility / future experimentation.
    llm_score = Column(
        Float,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Sprint 11 provenance / research metadata
    # ------------------------------------------------------------------

    prediction_source = Column(
        String(20),
        nullable=False,
        default="rule",
        server_default="rule",
        index=True,
    )

    feature_version = Column(
        String(80),
        nullable=True,
        index=True,
    )

    calibration_version = Column(
        String(80),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    # ------------------------------------------------------------------
    # Intervention helpers
    # ------------------------------------------------------------------

    @property
    def requires_hint(self) -> bool:
        """
        Return True when the diagnosis recommends progressive hints.
        """

        return (
            self.state == "confident"
            and self.next_action == "show_hint"
            and self.primary_misconception_id is not None
        )

    @property
    def requires_diagnostic_question(self) -> bool:
        """
        Return True when more targeted evidence should be collected.
        """

        return (
            self.state == "possible"
            and self.next_action == "ask_diagnostic_question"
            and self.primary_misconception_id is not None
        )

    @property
    def requires_clarification(self) -> bool:
        """
        Return True when the submission lacks sufficient evidence.
        """

        return (
            self.state == "insufficient"
            and self.next_action
            in {
                "ask_clarification",
                "ask_diagnostic_question",
            }
        )

    @property
    def is_final_without_intervention(self) -> bool:
        """
        Return True when no further student intervention is required.
        """

        return (
            self.state == "no_misconception"
            and self.next_action == "no_action"
        )

    # ------------------------------------------------------------------
    # Sprint 11 helpers
    # ------------------------------------------------------------------

    @property
    def is_rule_prediction(self) -> bool:
        """
        Return True when the final diagnosis came from the rule engine.
        """

        return self.prediction_source == "rule"

    @property
    def is_ml_prediction(self) -> bool:
        """
        Return True when the final diagnosis came from ML-only inference.
        """

        return self.prediction_source == "ml"

    @property
    def is_hybrid_prediction(self) -> bool:
        """
        Return True when the final diagnosis came from rule + ML fusion.
        """

        return self.prediction_source == "hybrid"

    @property
    def component_score(self) -> float | None:
        """
        Return the score most relevant to the diagnosis source.

        The canonical externally exposed confidence remains ``confidence``.
        This property is useful for evaluation/debugging only.
        """

        if self.prediction_source == "hybrid":
            return self.hybrid_score

        if self.prediction_source == "ml":
            return self.ml_score

        return self.rule_score

    def set_rule_prediction(
        self,
        *,
        score: float | None = None,
    ) -> None:
        """
        Mark this diagnosis as rule-engine generated.
        """

        self.prediction_source = "rule"
        self.rule_score = score

    def set_ml_prediction(
        self,
        *,
        score: float,
        feature_version: str | None = None,
        calibration_version: str | None = None,
    ) -> None:
        """
        Mark this diagnosis as ML-generated.
        """

        if score < 0.0 or score > 1.0:
            raise ValueError(
                "ML score must be between 0.0 and 1.0."
            )

        self.prediction_source = "ml"
        self.ml_score = score

        normalized_feature_version = (
            feature_version or ""
        ).strip()

        self.feature_version = (
            normalized_feature_version
            or None
        )

        normalized_calibration_version = (
            calibration_version or ""
        ).strip()

        self.calibration_version = (
            normalized_calibration_version
            or None
        )

    def set_hybrid_prediction(
        self,
        *,
        rule_score: float | None,
        ml_score: float,
        hybrid_score: float,
        feature_version: str | None = None,
        calibration_version: str | None = None,
    ) -> None:
        """
        Store rule, ML, and fused scores for a hybrid diagnosis.
        """

        scores = {
            "ml_score": ml_score,
            "hybrid_score": hybrid_score,
        }

        if rule_score is not None:
            scores["rule_score"] = rule_score

        for field_name, score in scores.items():
            if score < 0.0 or score > 1.0:
                raise ValueError(
                    f"{field_name} must be between 0.0 and 1.0."
                )

        self.prediction_source = "hybrid"

        self.rule_score = rule_score
        self.ml_score = ml_score
        self.hybrid_score = hybrid_score

        normalized_feature_version = (
            feature_version or ""
        ).strip()

        self.feature_version = (
            normalized_feature_version
            or None
        )

        normalized_calibration_version = (
            calibration_version or ""
        ).strip()

        self.calibration_version = (
            normalized_calibration_version
            or None
        )

    def __repr__(self) -> str:
        return (
            f"<Diagnosis("
            f"id={self.id}, "
            f"attempt_id={self.attempt_id}, "
            f"state={self.state!r}, "
            f"confidence={self.confidence}, "
            f"primary_misconception_id={self.primary_misconception_id}, "
            f"model_version={self.model_version!r}, "
            f"prediction_source={self.prediction_source!r}, "
            f"rule_score={self.rule_score}, "
            f"ml_score={self.ml_score}, "
            f"hybrid_score={self.hybrid_score}, "
            f"next_action={self.next_action!r}"
            f")>"
        )