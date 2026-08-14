# Misconception OS Model Card

**Model family:** Hybrid deterministic rule engine and baseline classifier
**Baseline version:** `baseline-logreg-v1.1`
**Fusion version:** `hybrid-fusion-v1.0`
**Document status:** Phase 1 engineering model card
**Last updated:** 14 August 2026

## 1. Model overview

Misconception OS analyses programming attempts to identify likely conceptual
misunderstandings and support an appropriate educational intervention.

The current system is not a single end-to-end neural model. It consists of:

1. deterministic evidence extraction;
2. problem-specific rule-based diagnosis;
3. an experimental logistic-regression classifier;
4. engineering rule-plus-ML fusion;
5. automatic rule-only fallback;
6. teacher review and override.

The deterministic rule engine remains the production safety path. The baseline
ML component is an experimental engineering baseline.

## 2. Intended use

The system is intended to:

- analyse student programming attempts;
- organize evidence from answers, reasoning, code, and speech transcripts;
- identify likely programming misconceptions;
- assign a diagnosis state and confidence;
- recommend educational interventions;
- support retries and follow-up diagnosis;
- assist teachers in reviewing diagnosis results;
- generate reviewed data for later model development.

The model is a decision-support tool. It does not replace teachers.

## 3. Out-of-scope and prohibited use

The system must not be used:

- as the sole basis for student grading;
- to make disciplinary or admission decisions;
- to evaluate teacher performance;
- to infer intelligence, disability, personality, or protected characteristics;
- as proof that a student intentionally cheated;
- for fully autonomous educational decisions without review;
- to execute untrusted student code directly on the application host;
- as a research-validated model before the planned pilot and evaluation;
- outside the supported programming problems without validation.

## 4. Inputs

The model can process structured fields including:

- final answer;
- written reasoning;
- source code;
- selected programming language;
- input language;
- optional speech transcript;
- response time;
- problem identifier;
- retry and parent-attempt information.

Raw speech audio is not required by the model. Speech transcripts are treated
as textual evidence.

A verified handwriting OCR pipeline is not currently part of the model.

## 5. Outputs

The diagnosis pipeline can produce:

- diagnosis state;
- primary misconception identifier;
- confidence score;
- rule score;
- ML score when available;
- hybrid score when available;
- prediction source;
- rule and ML component states;
- agreement status;
- model version;
- feature version;
- calibration version;
- evidence and provenance;
- intervention recommendation.

Supported diagnosis states include:

- `confident`;
- `possible`;
- `insufficient`;
- `no_misconception`.

## 6. System components

### 6.1 Evidence extractor

The evidence extractor normalizes the submitted attempt and derives structured
signals for the rule and ML components.

Its purpose is to make diagnosis behavior inspectable and repeatable.

### 6.2 Rule engine

The deterministic rule engine applies problem-specific misconception rules and
allowlists.

Strengths include:

- deterministic behavior;
- explainable evidence mapping;
- predictable fallback;
- problem-specific restrictions;
- straightforward testing;
- stable behavior with small datasets.

Limitations include:

- manual rule construction;
- limited transfer to unseen problems;
- dependence on rule quality;
- limited ability to learn subtle patterns automatically.

### 6.3 Baseline classifier

The experimental classifier uses logistic regression with persisted
preprocessing and model artifacts.

The current baseline validates:

- dataset loading;
- feature preparation;
- model training;
- model persistence;
- runtime inference;
- output mapping;
- integration with the diagnosis service.

It is not a transformer, large language model, or multimodal neural encoder.

### 6.4 Hybrid fusion

The fusion component combines rule and ML outputs when both are available.

The current fusion is engineering logic rather than learned or formally
calibrated fusion. Agreement and disagreement between components are preserved
for inspection.

### 6.5 Rule-only fallback

If ML is disabled, unavailable, incompatible, or fails during inference, the
service falls back to rule-only diagnosis.

Fallback prevents the experimental model from blocking the core educational
workflow.

## 7. Training data

The current baseline artifact was trained using a smoke dataset.

| Property | Value |
|---|---:|
| Total records | 24 |
| Training records | 18 |
| Test records | 6 |
| Classes | 4 |
| Dataset purpose | Engineering smoke validation |
| Research-training readiness | No |

The smoke dataset is not representative of the planned student population.

The current teacher-reviewed export contains six reviewed attempts. It proves
that the review and export pipeline works, but it is too small for
research-grade training or evaluation.

Additional dataset details are documented in
`docs/dataset/DATASET_CARD.md`.

## 8. Preliminary performance

The persisted smoke-test metrics report:

| Metric | Value |
|---|---:|
| Accuracy | 1.00 |
| Macro precision | 1.00 |
| Macro recall | 1.00 |
| Macro F1 | 1.00 |
| Test records | 6 |

These results must not be presented as production accuracy.

The perfect score is not statistically meaningful because:

- only six records are present in the test set;
- the dataset was created for smoke validation;
- individual class support is extremely small;
- the split is not formally grouped by student identity;
- the records do not represent the proposed student pilot;
- independent faculty labels are unavailable;
- external validation has not been performed.

The proposal target of macro F1 greater than or equal to `0.70` remains
unproven.

## 9. Calibration

The current system persists calibration metadata fields, but research-grade
confidence calibration has not been established.

Expected calibration error has not yet been measured.

Confidence values must therefore be interpreted as engineering signals rather
than statistically validated probabilities.

The proposal target of expected calibration error below `0.15` remains
pending.

## 10. Human validation

Teachers can:

- inspect diagnosis evidence;
- accept a diagnosis;
- override a diagnosis;
- reject a diagnosis;
- supply a corrected target state;
- contribute reviewed examples to dataset export.

Two independent faculty reviewers have not yet validated the complete
taxonomy.

Teacher-model Cohen's kappa has not yet been measured. The proposal target of
kappa greater than or equal to `0.60` remains pending.

## 11. Safety mechanisms

Implemented safety mechanisms include:

- deterministic production fallback;
- ML feature flag;
- graceful model-unavailable handling;
- prediction-source persistence;
- component-score persistence;
- teacher review and override;
- problem-specific misconception allowlists;
- insufficient-evidence state;
- anonymous student aliases;
- explicit consent requirement.

These mechanisms reduce risk but do not establish production safety by
themselves.

## 12. Known risks

### 12.1 Dataset risk

The current dataset is too small and may not represent:

- genuine student reasoning;
- different experience levels;
- diverse language backgrounds;
- unseen programming problems;
- uncommon misconception classes;
- accessibility-related input variation.

### 12.2 Automation bias

Teachers may over-trust a model-generated diagnosis. The interface and
training materials must reinforce that model output is advisory.

### 12.3 Confidence misinterpretation

Uncalibrated confidence may be mistaken for a reliable probability. Confidence
must be displayed with its source and limitations.

### 12.4 Language variation

Mixed-language reasoning, informal spelling, transliteration, and speech
transcription errors may change extracted evidence.

### 12.5 Problem transfer

Rules and baseline features validated for one problem may perform poorly on a
different problem.

### 12.6 Privacy risk

Reasoning, source code, and speech transcripts may contain personal
information. Collection and retention must be minimized.

### 12.7 Code-execution risk

The current model treats source code as text evidence. A restricted execution
sandbox has not been verified. Untrusted code must not be executed directly.

## 13. Fairness considerations

A formal fairness evaluation has not been conducted.

Phase 2 evaluation should measure performance across relevant and consented
groups, including:

- programming experience;
- input language;
- text-only versus multimodal submissions;
- speech usage;
- problem category;
- retry status.

Protected or sensitive attributes must not be collected without a documented
purpose, legal basis, consent process, and privacy review.

## 14. Privacy considerations

Current privacy-aware behavior includes:

- anonymous aliases;
- explicit consent;
- attempt rejection without consent;
- speech-processing status;
- explicit raw-audio retention metadata;
- non-retention of raw speech audio in demonstrated reviewed records.

Pending controls include:

- consent withdrawal;
- deletion following withdrawal;
- retention-policy enforcement;
- encryption-at-rest verification;
- production access review;
- formal security assessment.

## 15. Technical requirements

The baseline model depends on compatible versions of:

- Python;
- NumPy;
- pandas;
- scikit-learn;
- SciPy;
- joblib.

Model loading may fail if the persisted artifact is used with incompatible
dependency versions. The service must preserve rule-only fallback when an
artifact cannot be loaded safely.

## 16. Monitoring recommendations

A future production deployment should monitor:

- model availability;
- inference failures;
- fallback frequency;
- rule and ML disagreement;
- teacher override rate;
- class distribution;
- confidence distribution;
- insufficient-evidence rate;
- per-problem performance;
- inference latency;
- data drift;
- privacy and access events.

No automatic retraining should occur without dataset validation and approval.

## 17. Required Phase 2 validation

Before research or production claims are made, the project should:

1. collect 300–500 genuine consented attempts;
2. obtain labels from two faculty reviewers;
3. conduct the planned 20-student pilot;
4. define train, validation, and test splits by student identity;
5. measure macro precision, recall, and F1;
6. measure teacher-model Cohen's kappa;
7. measure expected calibration error;
8. compare rule-only and logistic-regression baselines;
9. implement and evaluate a text-only transformer baseline;
10. evaluate multimodal encoders where justified;
11. conduct modality ablation studies;
12. assess fairness, latency, resources, and learning effectiveness;
13. perform security and privacy review;
14. update this model card with validated results.

## 18. Model release status

| Component | Status |
|---|---|
| Rule engine | Engineering MVP |
| Logistic-regression baseline | Experimental |
| Hybrid fusion | Experimental |
| Rule-only fallback | Validated |
| Confidence calibration | Not validated |
| Transformer baseline | Not implemented |
| Neural multimodal model | Not implemented |
| Handwriting OCR | Not implemented |
| Restricted code sandbox | Not verified |
| Research acceptance | Pending |

## 19. Responsible-use statement

Misconception OS should augment teacher judgment by organizing evidence and
suggesting possible misconceptions.

Every high-impact interpretation must remain reviewable, correctable, and
traceable to the evidence used by the system.

## 20. Related documentation

- `docs/evaluation/EVALUATION_REPORT.md`
- `docs/dataset/DATASET_CARD.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/NEXT_PHASE_VALIDATION.md`
- `README.md`