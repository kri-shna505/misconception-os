# Misconception OS Known Limitations

**Document status:** Phase 1 customer disclosure
**Last updated:** 14 August 2026
**Applies to:** Sprint 11 engineering MVP

## 1. Purpose

This document records the known limitations of the current Misconception OS
engineering MVP.

It separates:

- validated capabilities;
- partially implemented capabilities;
- unimplemented proposal requirements;
- research claims that remain unproven;
- operational constraints for the customer demonstration.

The purpose is to prevent experimental functionality from being represented as
research-validated or production-ready functionality.

## 2. Current release position

The current release is suitable for:

- controlled engineering demonstrations;
- student and teacher workflow review;
- deterministic diagnosis testing;
- teacher-review workflow testing;
- reviewed-dataset export;
- baseline ML pipeline verification;
- customer feedback and Phase 2 planning.

The current release is not yet suitable for:

- unrestricted production deployment;
- autonomous grading;
- high-impact student decisions;
- research-effectiveness claims;
- processing untrusted code through direct execution;
- public dataset publication;
- large-scale institutional rollout.

## 3. Summary status

| Area | Current status | Severity |
|---|---|---|
| Core student workflow | Implemented | Low |
| Teacher review workflow | Implemented | Low |
| Rule-based diagnosis | Implemented | Low |
| Hybrid ML integration | Experimental | Medium |
| Rule-only fallback | Implemented and tested | Low |
| Genuine labelled dataset | Insufficient | High |
| Research-grade metrics | Not established | High |
| Confidence calibration | Not established | High |
| Faculty validation | Not completed | High |
| Student pilot | Not completed | High |
| Handwriting OCR | Not implemented | Medium |
| Restricted code sandbox | Not implemented | Critical for code execution |
| Consent capture | Implemented | Low |
| Consent withdrawal | Not implemented fully | High |
| Retention enforcement | Not implemented fully | High |
| Encryption-at-rest verification | Not completed | High |
| Fairness study | Not conducted | High |
| Learning-effectiveness study | Not conducted | High |
| Production security assessment | Not conducted | High |

## 4. Dataset limitations

The current ML smoke dataset contains 24 records.

The current teacher-reviewed export contains six reviewed attempts.

These datasets are insufficient to:

- represent genuine student diversity;
- estimate generalization reliably;
- establish stable per-class performance;
- evaluate uncommon misconceptions;
- perform dependable calibration;
- conduct fairness analysis;
- support research conclusions;
- support unrestricted production training.

The proposal requirement for 300–500 genuine labelled attempts remains
pending.

### Current mitigation

The current datasets are labelled as engineering artifacts.

Smoke metrics are documented separately from future research results.

## 5. Evaluation limitations

The current persisted baseline reports a macro F1 score of `1.00` on six smoke
test records.

This score is not accepted as proof that the proposal target has been met.

Reasons include:

- extremely small test set;
- engineered smoke examples;
- one or two test records per class;
- no formal validation set;
- no split by student identity;
- no independent faculty labels;
- no student pilot;
- no external evaluation.

### Current mitigation

Customer material must describe this as pipeline smoke validation.

The project must not advertise `100% model accuracy`.

## 6. Student-identity split limitation

Retries and related attempts may come from the same anonymous student.

The current smoke split is not a formal train, validation, and test split
grouped by student identity.

This creates a risk of information leakage and inflated metrics.

### Required resolution

Phase 2 must keep all records from the same student in one split.

Parent attempts and retries must also remain together.

## 7. Taxonomy-validation limitation

The misconception taxonomy has not been independently validated by two faculty
members.

Teacher-review functionality exists, but workflow existence is not equivalent
to independent expert validation.

Teacher-model Cohen's kappa has not been measured.

### Required resolution

Two faculty reviewers must independently label overlapping attempts without
seeing the model output during initial annotation.

Disagreements must be adjudicated after independent labels are preserved.

## 8. Student-pilot limitation

The proposed pilot with 20 students and two faculty reviewers has not been
conducted.

Consequently, the system has not yet established:

- usability with the intended population;
- realistic attempt distribution;
- educational effectiveness;
- teacher workload;
- intervention usefulness;
- real-world error behavior;
- deployment readiness.

### Current mitigation

The current release is positioned as a Phase 1 engineering MVP.

The pilot is explicitly listed as Phase 2 work.

## 9. Confidence-calibration limitation

The system stores confidence and calibration metadata, but research-grade
calibration has not been completed.

Expected calibration error has not been measured.

A displayed confidence value must not be interpreted as a statistically
validated probability.

### Current mitigation

The interface and documentation preserve prediction source and component
scores.

Teacher judgment remains authoritative.

## 10. Hybrid-fusion limitation

The current rule-plus-ML fusion is engineering logic.

It is not:

- learned from a representative dataset;
- calibrated against a held-out validation set;
- validated through an ablation study;
- proven superior to rule-only diagnosis.

### Current mitigation

Rule and ML component states are preserved separately.

If ML is unavailable or fails, the system returns to rule-only diagnosis.

## 11. Baseline-model limitation

The current baseline is logistic regression.

A text-only transformer baseline has not been implemented.

True multimodal neural encoders have not been implemented.

No formal comparison currently exists between:

- rule-only diagnosis;
- logistic regression;
- text transformer;
- code encoder;
- speech encoder;
- multimodal fusion variants.

### Required resolution

Phase 2 must define a fixed evaluation dataset and compare baselines under the
same split and metrics.

## 12. Speech limitation

The application supports optional speech transcripts and speech-processing
metadata.

The current implementation does not establish:

- speech-recognition accuracy;
- robustness to accents or noise;
- performance across languages;
- neural speech representation learning;
- educational value added by speech evidence.

Raw speech retention must remain disabled unless explicitly consented and
governed.

## 13. OCR limitation

A verified handwriting OCR pipeline is not implemented.

Image upload capability, if present, must not be represented as handwriting
recognition.

The system currently lacks validated:

- image preprocessing;
- handwriting text extraction;
- OCR confidence;
- OCR error handling;
- OCR accuracy metrics;
- handwriting-specific test data.

### Demo constraint

Do not demonstrate handwriting OCR as a completed feature.

If discussed, label it as Phase 2 scope.

## 14. Code-execution sandbox limitation

Student source code is treated as text evidence.

A restricted code-execution sandbox has not been verified.

The application does not currently demonstrate enforced:

- CPU limits;
- memory limits;
- execution time limits;
- process limits;
- network isolation;
- filesystem isolation;
- package restrictions;
- syscall restrictions;
- output-size limits.

Executing untrusted student code directly on the backend host would be unsafe.

### Demo constraint

Do not claim that submitted code is securely executed.

Describe it as source-code evidence analysis.

## 15. Security limitation

The project has automated tests and basic authentication-related controls, but
it has not undergone a formal production security assessment.

Pending security validation includes:

- threat modelling;
- dependency vulnerability review;
- authorization testing;
- secrets scanning;
- rate-limit testing;
- session-security review;
- production logging review;
- penetration testing;
- backup and recovery testing;
- incident-response planning.

### Current mitigation

The repository is private, local secrets are ignored, and customer
demonstration should occur in a controlled environment.

## 16. Encryption-at-rest limitation

Encryption-at-rest has not been independently verified for the database,
backups, model artifacts, and exported datasets.

Transport security and storage encryption depend on the final deployment
environment.

### Required resolution

The production architecture must document:

- database encryption;
- disk or volume encryption;
- backup encryption;
- key ownership;
- key rotation;
- access controls;
- recovery procedure.

## 17. Consent-withdrawal limitation

Explicit consent is required for student-session creation.

However, a complete consent-withdrawal workflow has not been demonstrated.

The current system does not yet prove:

- student withdrawal request submission;
- linked-record discovery;
- record deletion or anonymization;
- backup deletion behavior;
- withdrawal audit history;
- downstream dataset and model handling.

### Required resolution

Withdrawal behavior must be implemented and tested before production research
collection.

## 18. Retention-policy limitation

Speech-retention metadata exists, but a complete data-retention policy and
automatic enforcement mechanism are not implemented.

Pending work includes:

- per-data-type retention periods;
- scheduled deletion;
- legal-hold behavior;
- export expiration;
- backup retention;
- deletion verification.

## 19. De-identification limitation

Anonymous student aliases reduce direct identification but do not guarantee
anonymity.

Written reasoning, source code, file paths, timestamps, and speech transcripts
may contain direct or indirect identifiers.

### Current mitigation

Dataset exports must remain private and should be reviewed before external
sharing.

## 20. Fairness limitation

No formal fairness study has been conducted.

Unknown performance differences may exist across:

- programming experience;
- input language;
- speech use;
- modality availability;
- problem category;
- retry status;
- teaching context.

The system must not claim equal performance across groups.

## 21. Language limitation

The system supports English and normalized multilingual reasoning, including
Telugu-oriented workflows.

However, language coverage has not been evaluated systematically.

Potential failure sources include:

- transliteration;
- spelling variation;
- code switching;
- informal grammar;
- speech-transcription errors;
- technical terminology;
- unsupported languages.

## 22. Problem-generalization limitation

Rules are problem-specific.

Performance on one programming problem does not prove performance on another.

The baseline may also learn problem-specific shortcuts.

### Required resolution

Phase 2 should include multiple problem categories and problem-level holdout
evaluation.

## 23. Intervention-effectiveness limitation

The application can select interventions such as:

- hints;
- diagnostic questions;
- clarification requests;
- retry prompts;
- no action.

The project has not yet established that these interventions improve learning.

No controlled learning-effectiveness study has been conducted.

## 24. Latency and resource limitation

The system has passed functional smoke tests, but formal performance testing
has not been completed.

The project has not yet established production limits for:

- concurrent users;
- request throughput;
- database load;
- model inference latency;
- memory consumption;
- CPU consumption;
- export size;
- long-running sessions.

## 25. Browser and accessibility limitation

The frontend production build passes, but comprehensive browser and
accessibility certification has not been completed.

Pending validation includes:

- keyboard-only operation;
- screen-reader testing;
- color contrast;
- focus management;
- mobile layouts;
- browser compatibility;
- network interruption recovery;
- large-text behavior.

## 26. Warning debt

Backend tests currently pass with deprecation warnings.

Warnings include dependency and datetime-related deprecations.

They do not currently block the MVP, but ignoring them indefinitely will create
upgrade risk.

### Required resolution

Warnings should be categorized and reduced before a production release.

## 27. Deployment limitation

The current system has been validated primarily as a local and CI-tested
engineering project.

Production readiness still requires:

- deployment architecture;
- secure environment configuration;
- managed secrets;
- HTTPS;
- monitoring;
- alerting;
- backup and recovery;
- database migration procedure;
- rollback procedure;
- operational ownership;
- service-level objectives.

## 28. Research-deliverable limitation

The following proposal deliverables remain pending:

- final research evaluation package;
- validated model card;
- final dataset card;
- faculty agreement report;
- pilot report;
- technical report;
- research paper;
- poster;
- fairness report;
- learning-effectiveness report.

The current model card and dataset card are Phase 1 engineering disclosures,
not final research artifacts.

## 29. Demonstration guidance

During the customer demonstration, present:

- student session and consent;
- problem selection;
- multimodal evidence entry;
- deterministic diagnosis;
- hybrid ML integration;
- safe fallback;
- intervention and retry;
- teacher review;
- teacher override;
- student history;
- dataset export;
- CI and test evidence.

Do not present as completed:

- handwriting OCR;
- secure code execution;
- research-grade model accuracy;
- calibration target;
- faculty agreement target;
- full student pilot;
- fairness validation;
- production security certification.

## 30. Phase 1 completion statement

The defensible statement is:

> Phase 1 delivers a validated engineering MVP covering the principal student,
> teacher, diagnosis, intervention, review, dataset-export, baseline ML, and CI
> workflows. Research validation and advanced production controls remain Phase
> 2 work.

Do not state that the complete proposal is finished.

## 31. Related documentation

- `docs/evaluation/EVALUATION_REPORT.md`
- `docs/model/MODEL_CARD.md`
- `docs/dataset/DATASET_CARD.md`
- `docs/NEXT_PHASE_VALIDATION.md`
- `README.md`