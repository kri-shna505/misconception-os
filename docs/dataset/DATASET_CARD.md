# Misconception OS Dataset Card

**Dataset family:** Programming misconception diagnosis datasets
**Document status:** Phase 1 engineering dataset card
**Last updated:** 14 August 2026
**Maintainer:** Misconception OS project team

## 1. Dataset summary

Misconception OS uses structured programming-attempt records to support
misconception diagnosis, teacher review, and experimental model development.

The repository currently contains two different dataset categories:

1. a smoke training dataset created to validate the ML pipeline;
2. a teacher-reviewed export generated through application review workflows.

These datasets have different purposes and must not be combined in reporting
without clearly identifying their source.

Neither dataset currently satisfies the full proposal requirement for
300–500 genuine labelled student attempts.

## 2. Intended uses

The current datasets may be used for:

- testing dataset construction;
- validating feature extraction;
- validating training scripts;
- validating persisted model artifacts;
- testing inference and label mapping;
- testing rule-plus-ML fusion;
- testing teacher-review export;
- controlled engineering demonstrations;
- developing the Phase 2 data-collection protocol.

The current datasets must not be used as evidence of general educational or
research effectiveness.

## 3. Prohibited uses

The datasets must not be used:

- to claim production model accuracy;
- to claim the proposal's macro F1 target has been achieved;
- to rank or grade individual students;
- to infer intelligence, disability, personality, or protected attributes;
- to make admissions or disciplinary decisions;
- to train an unrestricted production model;
- to publish student-level records without privacy review;
- to re-identify anonymous student aliases;
- outside the documented consent and retention conditions.

## 4. Dataset inventory

### 4.1 Smoke training dataset

Repository locations:

- `backend/ml/data/exports/smoke_training_dataset.csv`
- `backend/ml/data/exports/smoke_training_dataset.jsonl`

| Property | Value |
|---|---:|
| Total records | 24 |
| Training records used by baseline | 18 |
| Test records used by baseline | 6 |
| Target classes | 4 |
| Primary purpose | Engineering smoke validation |
| Genuine research dataset | No |
| Serious training readiness | No |

The smoke dataset is designed to exercise expected pipeline paths and target
classes. It is not a representative sample of real student behavior.

### 4.2 Teacher-reviewed dataset

Repository locations:

- `backend/ml/data/exports/teacher_reviewed_dataset.csv`
- `backend/ml/data/exports/teacher_reviewed_dataset.jsonl`

| Property | Current value |
|---|---:|
| Reviewed attempts | 6 |
| Primary purpose | Review/export pipeline validation |
| Teacher decisions represented | Accepted and overridden |
| Text evidence | Present |
| Source-code evidence | Present |
| Speech transcript evidence | Present in a limited example |
| Raw speech retained | No in observed reviewed records |
| Research-training readiness | No |

The reviewed export demonstrates that teacher feedback can be converted into a
structured supervised-learning target. Its current size is too small for
dependable training, calibration, or subgroup analysis.

## 5. Unit of observation

One record represents one submitted programming attempt associated with:

- an anonymous student alias;
- a programming problem;
- an optional parent attempt;
- a retry number;
- the submitted evidence;
- the system diagnosis;
- an optional teacher review;
- the corrected or accepted target label.

Retries may produce multiple records associated with the same anonymous
student. Such records are not statistically independent.

Future train, validation, and test splits must group records by student
identity to prevent leakage.

## 6. Data fields

The export can contain fields including:

### 6.1 Identifiers and relationships

- `attempt_id`;
- `student_alias_id`;
- `problem_id`;
- `parent_attempt_id`;
- `retry_number`;
- `teacher_review_id`.

### 6.2 Student evidence

- `final_answer`;
- `written_reasoning`;
- `normalized_reasoning`;
- `source_code`;
- `speech_transcript`;
- `selected_language`;
- `input_language`;
- `input_modality`;
- `response_time_seconds`;
- `speech_processing_status`;
- `speech_audio_retained`.

### 6.3 Rule and model outputs

- `rule_state`;
- `rule_misconception_id`;
- `rule_confidence`;
- `rule_score`;
- `prediction_source`;
- `ml_score`;
- `hybrid_score`;
- `model_version`;
- `feature_version`;
- `calibration_version`.

### 6.4 Teacher targets

- `teacher_decision`;
- `target_state`;
- `target_misconception_id`.

### 6.5 Audit information

- `created_at`.

## 7. Label definitions

The primary diagnosis-state labels are:

### `confident`

Available evidence strongly supports a recognized misconception.

### `possible`

Evidence suggests a misconception but is not strong enough for a confident
diagnosis.

### `insufficient`

The submitted evidence is too incomplete, unclear, or unrelated to support a
reliable misconception diagnosis.

### `no_misconception`

The available evidence does not support a known misconception for the selected
problem.

A state label is separate from a misconception identifier. For example,
`insufficient` and `no_misconception` may not require a misconception ID.

## 8. Teacher-review labels

Teacher review can produce decisions such as:

- accepted;
- overridden;
- rejected, where supported by the workflow.

An accepted decision confirms the reviewed system output.

An overridden decision supplies a corrected target state or misconception.

Teacher-review records should preserve both:

- the original system prediction;
- the final teacher target.

This separation is necessary for later agreement and error analysis.

## 9. Data creation

### 9.1 Smoke data

Smoke records are constructed to cover expected classes and technical code
paths.

They are useful for detecting broken pipelines, but they can create
artificially easy classification boundaries.

### 9.2 Reviewed data

Reviewed records originate from attempts processed by the application and then
evaluated through the teacher workflow.

The current reviewed export contains too few records to determine:

- population-level class frequencies;
- authentic error diversity;
- inter-rater reliability;
- model generalization;
- subgroup performance;
- calibration;
- educational effectiveness.

## 10. Consent and privacy

The application requires explicit consent before creating a student session.

Attempts without consent are rejected by backend validation.

Privacy-aware fields and behavior include:

- anonymous student aliases;
- explicit consent state;
- speech-processing status;
- explicit speech-retention state;
- raw audio disabled in observed reviewed records.

The text fields may still contain personal information entered by a student.
Anonymous aliases alone do not guarantee complete de-identification.

Before external sharing, exports must be reviewed for:

- names;
- email addresses;
- phone numbers;
- usernames;
- institutional identifiers;
- file paths;
- secrets or API keys inside source code;
- personal information inside speech transcripts;
- indirect identifiers.

## 11. Sensitive and potentially identifying content

Potentially sensitive fields include:

- written reasoning;
- source code;
- speech transcripts;
- response timestamps;
- retry history;
- problem-performance patterns.

These fields may reveal identity or educational characteristics when combined
with external information.

Dataset access must follow least-privilege principles.

## 12. Current data-quality limitations

Known limitations include:

- only 24 smoke records;
- only six teacher-reviewed records;
- very small per-class support;
- constructed smoke examples;
- repeated or related attempts;
- limited problem coverage;
- limited programming-language coverage;
- limited speech evidence;
- no verified handwriting OCR evidence;
- no formal double annotation;
- no independent adjudication;
- no faculty agreement measurement;
- no student-identity grouped split;
- no representative pilot population;
- no systematic missing-data analysis;
- no fairness analysis.

## 13. Leakage risks

Potential leakage can occur when:

- retries from the same student are split across train and test sets;
- near-duplicate answers occur in different splits;
- rule-derived fields are used to predict teacher targets;
- model output fields are accidentally included as input features;
- examples created from the same template appear in multiple splits;
- problem identity directly reveals the expected label distribution.

Phase 2 splitting must occur before model training and must group by anonymous
student identity.

Near-duplicate detection should also be applied.

## 14. Current split status

The current smoke baseline uses:

- 18 training records;
- six test records.

This split is appropriate only for engineering smoke validation.

It is not a formal research split and does not prove generalization.

The proposal requirement for train, validation, and test splitting by student
identity remains pending.

## 15. Current evaluation status

The smoke model reports perfect metrics on six test records.

Those metrics are not accepted as research evidence because:

- the test set is extremely small;
- support per class is one or two records;
- the data is engineered;
- the split is not student-grouped;
- independent labels are unavailable.

See `docs/evaluation/EVALUATION_REPORT.md` for the complete interpretation.

## 16. Representativeness

The current datasets do not establish representation across:

- student experience levels;
- institutions;
- age groups;
- input languages;
- programming languages;
- accessibility requirements;
- problem categories;
- text, code, and speech modalities;
- misconception frequency;
- different teaching contexts.

No demographic representativeness claim should be made.

## 17. Annotation status

The proposal requires two faculty members to validate the taxonomy and review
labels.

That process has not yet been completed.

The current teacher-reviewed export demonstrates workflow capability, not
independent double annotation.

Cohen's kappa cannot be validly calculated until overlapping records are
independently labelled by at least two qualified reviewers.

## 18. Phase 2 collection target

Phase 2 should collect between 300 and 500 genuine, consented, labelled
student attempts.

The collection should include:

- at least 20 participating students;
- two independent faculty reviewers;
- multiple programming problems;
- meaningful misconception coverage;
- retries and successful corrections;
- text and source-code evidence;
- optional speech evidence where consented;
- documented missing-modality cases.

The target should be treated as a minimum evaluation dataset, not automatically
as sufficient for production deployment.

## 19. Recommended annotation protocol

Each selected attempt should be reviewed independently by two faculty members.

Reviewers should record:

- evidence sufficiency;
- diagnosis state;
- primary misconception;
- optional secondary misconception;
- confidence in the annotation;
- rationale;
- whether intervention is needed;
- recommended intervention type.

Reviewers should not see the model prediction during initial independent
annotation.

Disagreements should be adjudicated only after the independent labels are
stored.

## 20. Recommended split protocol

The final dataset should be divided into:

- training set;
- validation set;
- held-out test set.

Required constraints:

1. all records from one student remain in one split;
2. parent attempts and retries remain in the same split;
3. duplicates and near-duplicates remain in one split;
4. the held-out test set is frozen before final training;
5. test labels are not used for feature or threshold tuning;
6. split statistics are recorded and versioned;
7. random seeds and scripts are preserved.

Problem-level holdout should also be considered to evaluate transfer to unseen
problems.

## 21. Recommended quality checks

Before training, validate:

- identifier uniqueness;
- foreign-key consistency;
- valid label values;
- misconception allowlist compatibility;
- missing fields;
- invalid response times;
- duplicate attempts;
- near-duplicate reasoning;
- accidental personal information;
- secrets inside source code;
- unsupported languages;
- corrupted Unicode;
- transcript quality;
- class distribution;
- student distribution;
- problem distribution;
- modality distribution.

## 22. Retention and withdrawal

A production dataset process must define:

- consent version;
- collection purpose;
- collection timestamp;
- retention period;
- withdrawal request mechanism;
- deletion procedure;
- backup-deletion behavior;
- authorized roles;
- export approval;
- research-use approval.

Consent withdrawal and retention enforcement are not yet fully implemented.

## 23. Dataset versioning

Future dataset releases should include:

- immutable version identifier;
- creation timestamp;
- source query or export version;
- schema version;
- annotation-guideline version;
- reviewer information or pseudonymous reviewer IDs;
- split manifest;
- class statistics;
- modality statistics;
- quality-check results;
- change log;
- checksum.

The current smoke and reviewed exports should be treated as Phase 1
engineering artifacts.

## 24. Known biases

Potential biases include:

- overrepresentation of one programming problem;
- teacher-specific annotation preferences;
- rule-generated label influence;
- English-dominant feature behavior;
- underrepresentation of speech inputs;
- limited Telugu and mixed-language coverage;
- synthetic smoke-example simplicity;
- successful-attempt selection bias;
- repeated-student effects.

These risks have not yet been quantitatively measured.

## 25. Access and distribution

The repository is private.

Dataset exports should remain private unless:

- consent permits the proposed use;
- personal information is removed;
- customer approval is obtained;
- institutional requirements are satisfied;
- access controls are documented.

Raw production data should not be committed to Git.

## 26. Dataset release status

| Dataset | Status |
|---|---|
| Smoke training dataset | Engineering-only |
| Teacher-reviewed export | Preliminary |
| Research dataset | Not collected |
| Faculty-validated dataset | Pending |
| Student-pilot dataset | Pending |
| Public dataset | Not approved |

## 27. Related documentation

- `docs/evaluation/EVALUATION_REPORT.md`
- `docs/model/MODEL_CARD.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/NEXT_PHASE_VALIDATION.md`
- `README.md`

## 28. Responsible-use statement

The dataset exists to improve educational support, not to automate high-impact
judgments about students.

Every dataset release and model trained from it must preserve consent,
traceability, teacher oversight, and the ability to correct or remove records.