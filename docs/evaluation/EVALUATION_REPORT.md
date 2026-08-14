# Misconception OS Evaluation Report

**Document status:** Phase 1 engineering evaluation
**Evaluation date:** 14 August 2026
**System milestone:** Sprint 11
**Repository:** `axion-5025/misconceptionos`

## 1. Executive summary

Misconception OS is an AI-assisted learning system that identifies likely
programming misconceptions from student answers, written reasoning, source
code, and optional speech transcripts.

The current release is a validated engineering MVP. It includes deterministic
rule-based diagnosis, a baseline machine-learning model, hybrid rule-plus-ML
fusion, safe rule-only fallback, teacher review workflows, dataset export,
database migrations, automated backend tests, and frontend quality checks.

The available evaluation confirms that the software pipeline works as designed.
It does not yet establish research-grade model effectiveness because the
available labelled dataset is small and has not been collected through the
planned student pilot.

## 2. Evaluation scope

This report evaluates the following Phase 1 areas:

- backend functionality and regression safety;
- database migration consistency;
- frontend linting and production compilation;
- rule-based diagnosis behavior;
- baseline ML training and persisted-model loading;
- rule-plus-ML fusion;
- rule-only fallback behavior;
- teacher-reviewed dataset export;
- preliminary baseline classification metrics;
- readiness gaps against the full project proposal.

This report does not claim completion of the planned research study, faculty
validation, or student pilot.

## 3. Evaluated system

The evaluated system contains:

- FastAPI backend services;
- PostgreSQL persistence;
- SQLAlchemy models and Alembic migrations;
- React and TypeScript frontend;
- deterministic evidence extraction;
- rule-based misconception diagnosis;
- logistic-regression baseline model;
- hybrid rule-plus-ML prediction fusion;
- automatic rule-only fallback;
- student attempt and retry workflows;
- teacher review and override workflows;
- reviewed-dataset export;
- CI workflows for backend and frontend validation.

## 4. Engineering validation results

| Validation area | Result | Evidence |
|---|---:|---|
| Backend automated tests | Passed | 340 tests passed |
| Backend warnings | Non-blocking | 367 deprecation warnings |
| Diagnosis-service tests | Passed | 39 focused tests passed |
| Alembic revision | Passed | Database revision matched current head |
| Frontend lint | Passed | 0 errors; warnings remained |
| Frontend production build | Passed | TypeScript and Vite build completed |
| Backend CI | Passed | GitHub Actions migration and test workflow |
| Frontend CI | Passed | GitHub Actions lint and build workflow |
| Persisted ML artifact loading | Passed | Joblib baseline model loaded successfully |
| Hybrid inference smoke test | Passed | Rule-plus-ML fusion returned a result |
| Rule-only regression mode | Passed | Diagnosis remained available with ML disabled |
| ML failure fallback | Passed | Rule diagnosis preserved when ML was unavailable |

## 5. Baseline dataset

Two dataset categories currently exist.

### 5.1 Smoke training dataset

The smoke dataset is intended to validate the training and inference pipeline.
It is not a genuine research dataset.

| Property | Value |
|---|---:|
| Total records | 24 |
| Training records | 18 |
| Test records | 6 |
| Target classes | 4 |
| Dataset purpose | Pipeline smoke validation |
| Research-training readiness | No |

The four target states are:

- `confident`;
- `possible`;
- `insufficient`;
- `no_misconception`.

### 5.2 Teacher-reviewed export

The current teacher-reviewed JSONL export contains six reviewed attempts.

This export demonstrates that the application can:

- preserve attempt and problem references;
- associate records with anonymous student aliases;
- capture teacher decisions;
- retain rule state and confidence;
- capture accepted and overridden outcomes;
- generate target states for later supervised training;
- include text, code, and optional speech transcript fields.

Six reviewed attempts are insufficient for dependable model training,
calibration, subgroup analysis, or statistical conclusions.

## 6. Preliminary baseline metrics

The persisted baseline metrics currently report:

| Metric | Recorded value |
|---|---:|
| Accuracy | 1.00 |
| Macro precision | 1.00 |
| Macro recall | 1.00 |
| Macro F1 | 1.00 |
| Test records | 6 |

These values must be interpreted only as smoke-test results.

The perfect score does not establish production or research performance because:

- the test set contains only six records;
- the smoke records are engineered for pipeline verification;
- the data does not represent 300–500 genuine student attempts;
- the split is not formally grouped by student identity;
- class support ranges from one to two test records;
- independent faculty validation has not been completed;
- the planned 20-student pilot has not been conducted;
- calibration and inter-rater agreement have not been measured.

The proposal target of macro F1 greater than or equal to `0.70` is therefore
not yet considered proven.

## 7. Rule and ML behavior

### 7.1 Rule-based diagnosis

The deterministic rule engine is the current production safety path. It
extracts evidence from the supplied answer, reasoning, source code, language,
and optional speech transcript.

The rule engine supports:

- problem-specific misconception allowlists;
- confidence and diagnosis states;
- insufficient-evidence handling;
- no-misconception outcomes;
- provenance and component-score persistence;
- retry and follow-up diagnosis workflows.

### 7.2 Baseline ML model

The current ML component uses a logistic-regression baseline with persisted
preprocessing and model artifacts.

Its present purpose is to verify:

- feature construction;
- training reproducibility;
- artifact persistence;
- runtime model loading;
- prediction mapping;
- integration with the diagnosis service.

It is not a transformer baseline or a true multimodal neural model.

### 7.3 Hybrid fusion and fallback

When ML diagnosis is enabled and available, the service combines rule and ML
outputs using engineering fusion logic.

When ML is disabled, unavailable, or fails, the system automatically returns
to rule-only diagnosis. This prevents experimental ML availability from
blocking the core student workflow.

The fusion confidence is not yet research-grade calibrated confidence.

## 8. Proposal metric status

| Proposal requirement | Current status |
|---|---|
| Macro F1 greater than or equal to 0.70 | Not yet proven on representative held-out data |
| Teacher-model Cohen's kappa greater than or equal to 0.60 | Not yet measured |
| Expected calibration error below 0.15 | Not yet measured |
| Train/validation/test split by student identity | Not yet implemented formally |
| 300–500 genuine labelled attempts | Not yet collected |
| Two faculty taxonomy validators | Not yet completed |
| Pilot with 20 students and two faculty reviewers | Not yet conducted |
| Text-only transformer baseline | Not implemented |
| Multimodal neural encoders | Not implemented |
| Modality ablation study | Not conducted |
| Fairness evaluation | Not conducted |
| Learning-effectiveness evaluation | Not conducted |
| Formal latency and resource study | Not conducted |

## 9. OCR and source-code execution status

### 9.1 OCR

A verified handwriting OCR pipeline is not currently implemented.

The system must not be represented as performing reliable handwriting
recognition until image preprocessing, OCR extraction, error handling,
evaluation data, and accuracy reporting are implemented and tested.

### 9.2 Restricted code sandbox

Student source code is currently treated as diagnosis evidence. A restricted
code-execution sandbox with enforced CPU, memory, network, process, and
filesystem limits has not been verified.

Untrusted student code must not be executed directly by the application host.
Secure code execution remains a Phase 2 engineering requirement.

## 10. Privacy and governance status

Implemented controls include:

- anonymous student aliases;
- explicit consent requirement for session creation;
- rejection of attempts without consent;
- explicit speech-processing status;
- raw speech-retention metadata;
- raw speech retention disabled by default in demonstrated data.

The following controls require additional implementation or formal
verification:

- consent withdrawal workflow;
- record deletion following withdrawal;
- documented retention periods;
- scheduled retention enforcement;
- encryption-at-rest verification;
- access-control and audit review;
- data-subject request procedure;
- production security assessment.

## 11. Current strengths

The Phase 1 system demonstrates:

- a functional end-to-end student workflow;
- a functional teacher review workflow;
- deterministic and explainable diagnosis;
- safe rule-only fallback;
- persisted diagnosis provenance;
- repeatable ML pipeline execution;
- teacher-reviewed dataset generation;
- comprehensive backend regression coverage;
- automated backend and frontend CI;
- database migration consistency;
- clear separation between engineering validation and research validation.

## 12. Current limitations

The primary limitations are:

- small and non-representative labelled dataset;
- smoke-test metrics that cannot be generalized;
- absence of independent faculty validation;
- absence of a formal student pilot;
- no research-grade confidence calibration;
- no Cohen's kappa measurement;
- no student-grouped evaluation split;
- no transformer or neural multimodal baseline;
- no verified OCR pipeline;
- no restricted code-execution sandbox;
- incomplete privacy-lifecycle controls;
- no formal fairness or learning-effectiveness study.

Detailed limitations are maintained separately in
`docs/KNOWN_LIMITATIONS.md`.

## 13. Phase 1 conclusion

The engineering MVP is validated for controlled demonstration.

The completed validation establishes that the software components, database
migrations, student and teacher workflows, diagnosis services, baseline model
pipeline, fallback behavior, and CI checks operate successfully.

It does not establish research-grade model accuracy or educational
effectiveness.

The correct delivery position is:

> Misconception OS Phase 1 delivers a validated engineering MVP with
> deterministic diagnosis, an experimental baseline ML integration, teacher
> review, dataset export, automated testing, and safe fallback. Research-scale
> dataset collection, independent faculty validation, pilot evaluation, secure
> code execution, OCR, and advanced multimodal modelling remain Phase 2 work.

## 14. Phase 2 evaluation plan

The next validation phase should:

1. recruit two faculty taxonomy reviewers;
2. define a written annotation protocol;
3. collect 300–500 consented and genuinely labelled attempts;
4. conduct a pilot with at least 20 students;
5. separate train, validation, and test sets by student identity;
6. establish majority or adjudicated faculty labels;
7. train rule, logistic-regression, and transformer baselines;
8. calculate macro precision, recall, and F1;
9. calculate teacher-model Cohen's kappa;
10. calculate expected calibration error;
11. report per-class confusion matrices;
12. evaluate modality ablations;
13. measure fairness, latency, and resource use;
14. assess learning effectiveness;
15. publish the final technical evaluation report.

## 15. Reproduction references

Primary implementation and evidence locations:

- `backend/tests/`
- `backend/app/ml/`
- `backend/app/services/ml_diagnosis_service.py`
- `backend/ml/training/`
- `backend/ml/data/exports/`
- `backend/ml/models/baseline/baseline_metrics.json`
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`

## 16. Approval status

This document supports a Phase 1 engineering demonstration and customer review.

Research acceptance remains pending completion of the Phase 2 validation plan.