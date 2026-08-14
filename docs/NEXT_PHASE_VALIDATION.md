# Misconception OS Next-Phase Validation Plan

**Plan status:** Proposed Phase 2
**Prepared:** 14 August 2026
**Starting point:** Validated Phase 1 engineering MVP
**Purpose:** Complete research validation and production-readiness work

## 1. Executive summary

Phase 1 delivered the principal engineering workflows for students, teachers,
diagnosis, intervention, review, dataset export, baseline machine learning,
safe fallback, database migrations, automated tests, and CI.

Phase 2 addresses the remaining proposal requirements that require genuine
participants, faculty involvement, representative data, research evaluation,
security engineering, privacy controls, and customer decisions.

Phase 2 must not begin formal participant data collection until the customer
approves:

- pilot scope;
- consent material;
- participating faculty;
- participant recruitment;
- data-retention policy;
- deployment environment;
- evaluation protocol.

## 2. Phase 2 objectives

Phase 2 will aim to:

1. validate the misconception taxonomy with two faculty members;
2. conduct a pilot involving at least 20 students;
3. collect 300–500 genuine consented attempts;
4. establish reliable teacher-reviewed labels;
5. create student-grouped train, validation, and test splits;
6. measure research acceptance metrics;
7. compare model baselines and modalities;
8. evaluate OCR feasibility;
9. implement restricted code execution if approved;
10. complete privacy and security controls;
11. evaluate fairness, latency, resources, and learning effectiveness;
12. prepare final technical and research deliverables.

## 3. Entry criteria

Phase 2 may begin when:

- Phase 1 documentation is approved;
- the engineering MVP is deployed in a controlled environment;
- backend and frontend CI pass;
- the customer nominates two faculty reviewers;
- pilot participants can be recruited;
- consent language is approved;
- data ownership is defined;
- retention and withdrawal requirements are approved;
- the customer accepts the known limitations;
- responsibilities and timeline are agreed.

## 4. Workstream overview

| Workstream | Primary outcome | Dependency |
|---|---|---|
| Faculty taxonomy validation | Approved taxonomy and annotation guide | Two faculty reviewers |
| Student pilot | Genuine usage evidence | 20 consented students |
| Dataset construction | 300–500 labelled attempts | Pilot and reviews |
| Statistical evaluation | F1, kappa, ECE and error analysis | Frozen test set |
| Model comparison | Rule, logistic and transformer baselines | Valid dataset |
| Multimodal evaluation | Modality and ablation results | Sufficient modality data |
| OCR | Verified handwriting pipeline or rejection decision | Image dataset |
| Code sandbox | Restricted execution service | Security approval |
| Privacy and governance | Withdrawal, retention and encryption controls | Customer policy |
| Operational evaluation | Fairness, latency and resource reports | Pilot deployment |
| Research deliverables | Final report, paper and poster | Completed evaluation |

## 5. Workstream 1: Faculty taxonomy validation

### Objective

Validate that the misconception taxonomy is educationally meaningful,
sufficiently clear, and consistently applicable.

### Required participants

- Faculty Reviewer A;
- Faculty Reviewer B;
- project adjudicator.

### Activities

1. review every misconception definition;
2. review positive and negative examples;
3. review problem-specific allowlists;
4. identify overlapping or ambiguous categories;
5. define evidence-sufficiency rules;
6. define primary versus secondary misconceptions;
7. approve diagnosis-state definitions;
8. approve intervention mapping;
9. publish annotation guidelines;
10. version the accepted taxonomy.

### Deliverables

- taxonomy review register;
- approved taxonomy version;
- annotation handbook;
- example library;
- disagreement-resolution procedure;
- faculty approval record.

### Acceptance criteria

- both faculty reviewers complete independent taxonomy review;
- unresolved category ambiguity is documented;
- annotation guidance is approved;
- taxonomy version is frozen before pilot labelling.

## 6. Workstream 2: Student pilot

### Objective

Observe the complete student and teacher workflows with genuine users.

### Minimum scope

- at least 20 students;
- two faculty reviewers;
- multiple programming problems;
- text and code evidence;
- optional speech evidence with consent;
- retry and intervention flows;
- teacher review of selected attempts.

### Activities

1. provide participant information;
2. collect explicit consent;
3. create anonymous aliases;
4. assign programming tasks;
5. collect initial attempts;
6. deliver interventions;
7. collect retry attempts;
8. collect usability feedback;
9. conduct teacher reviews;
10. record operational incidents.

### Pilot success criteria

- at least 20 consented students participate;
- no critical data-loss incident occurs;
- consent is recorded for every attempt;
- student and teacher workflows complete successfully;
- review and export pipelines operate;
- withdrawal requests can be handled;
- pilot findings are documented.

### Stop conditions

The pilot must pause if:

- consent is not recorded;
- personal data is exposed;
- unauthorized access occurs;
- untrusted code executes outside an approved sandbox;
- critical diagnosis or workflow corruption occurs;
- the customer requests suspension.

## 7. Workstream 3: Dataset collection

### Objective

Create a representative, consented and reviewable research dataset.

### Target

Collect between 300 and 500 genuine labelled attempts.

The target should include:

- initial attempts;
- retry attempts;
- correct and incorrect responses;
- insufficient-evidence cases;
- multiple misconception categories;
- multiple programming problems;
- different experience levels;
- English, Telugu and mixed-language examples where available;
- missing-modality examples;
- optional speech examples with explicit consent.

### Required metadata

Each record should preserve:

- anonymous student identifier;
- problem identifier;
- parent and retry relationships;
- input modality;
- submitted evidence;
- model and rule versions;
- initial system prediction;
- independent faculty labels;
- adjudicated label;
- consent version;
- collection timestamp;
- dataset version.

### Acceptance criteria

- at least 300 eligible attempts;
- every record has valid consent;
- every research label has reviewer provenance;
- personal information is removed or controlled;
- quality checks pass;
- class and problem distributions are reported;
- dataset version and checksum are generated.

## 8. Workstream 4: Annotation and adjudication

### Independent review

Two faculty members should independently label an overlapping evaluation
subset.

During initial annotation, reviewers must not see:

- the model prediction;
- the other reviewer's label;
- system confidence;
- system intervention.

### Reviewer fields

Each reviewer records:

- evidence sufficiency;
- diagnosis state;
- primary misconception;
- optional secondary misconception;
- annotation confidence;
- rationale;
- recommended intervention.

### Adjudication

After independent labels are stored:

1. compare reviewer decisions;
2. calculate inter-rater agreement;
3. discuss disagreements;
4. record adjudicated labels;
5. preserve original labels;
6. document taxonomy changes.

### Acceptance criteria

- overlapping records are independently reviewed;
- original labels remain immutable;
- adjudication is traceable;
- Cohen's kappa is calculated;
- agreement target is evaluated honestly.

## 9. Workstream 5: Dataset splitting

### Objective

Prevent identity and retry leakage across evaluation splits.

### Required split

Create:

- training set;
- validation set;
- held-out test set.

### Mandatory rules

- one student's attempts remain in one split;
- retries remain with their parent attempt;
- duplicates remain in one split;
- near-duplicates remain in one split;
- held-out test data is frozen;
- thresholds use validation data only;
- test data is evaluated only after model selection;
- split manifests are versioned;
- random seeds are recorded.

### Recommended evaluation

In addition to student-grouped splitting, evaluate:

- unseen-problem holdout;
- input-language subgroups;
- modality subgroups;
- retry versus initial attempts.

## 10. Workstream 6: Research metrics

### Primary metrics

Report:

- macro precision;
- macro recall;
- macro F1;
- per-class precision;
- per-class recall;
- per-class F1;
- confusion matrix;
- accuracy as a secondary metric.

### Agreement metric

Calculate teacher-model Cohen's kappa using the frozen evaluation set.

### Calibration metric

Calculate expected calibration error using held-out predictions.

Also consider:

- reliability diagrams;
- Brier score;
- confidence histograms;
- selective accuracy at confidence thresholds.

### Proposal acceptance targets

| Metric | Target |
|---|---:|
| Macro F1 | Greater than or equal to 0.70 |
| Teacher-model Cohen's kappa | Greater than or equal to 0.60 |
| Expected calibration error | Below 0.15 |

A failed target must be reported as failed. It must not be hidden by selecting
a more favorable subset after evaluation.

## 11. Workstream 7: Model baselines

### Required comparisons

Evaluate:

1. majority-class baseline;
2. deterministic rule-only system;
3. logistic-regression baseline;
4. text-only transformer baseline;
5. approved code-aware baseline;
6. approved multimodal model.

### Comparison controls

All models must use:

- the same frozen splits;
- the same label definitions;
- the same primary metrics;
- documented preprocessing;
- recorded hyperparameters;
- reproducible random seeds;
- versioned artifacts.

### Acceptance criteria

- baseline results are reproducible;
- rule-only results are included;
- model-selection decisions use validation data;
- test results are reported once per approved experiment;
- final model choice includes accuracy, safety, latency and interpretability.

## 12. Workstream 8: Multimodal and ablation evaluation

### Objective

Measure whether each modality provides real value.

### Candidate modalities

- final answer;
- written reasoning;
- source code;
- speech transcript;
- OCR text, only if OCR is approved and validated.

### Required ablations

Compare:

- answer only;
- answer plus reasoning;
- answer plus code;
- answer plus speech transcript;
- text plus code;
- all available modalities.

### Acceptance criteria

- modality availability is reported;
- missing modalities are handled explicitly;
- improvements are measured on the same test set;
- added complexity is justified by measurable benefit;
- modality-specific risks are documented.

## 13. Workstream 9: OCR validation

### Decision gate

The customer must confirm whether handwriting OCR is required for Phase 2.

### If approved

Implement and evaluate:

- image upload validation;
- file-type restrictions;
- file-size restrictions;
- malware scanning;
- image preprocessing;
- OCR extraction;
- OCR confidence;
- low-confidence handling;
- manual correction;
- deletion and retention behavior;
- handwriting-specific test set;
- OCR accuracy report.

### Acceptance criteria

- supported image formats are documented;
- unsafe files are rejected;
- OCR failures do not block manual input;
- OCR accuracy is measured;
- extracted text is reviewable;
- privacy and retention are approved.

If meaningful accuracy cannot be established, OCR must remain experimental.

## 14. Workstream 10: Restricted code sandbox

### Decision gate

The customer must confirm whether student code must be executed.

If execution is not required, source code should remain text evidence.

### If approved

The execution service must be isolated from the application host and enforce:

- CPU limits;
- memory limits;
- wall-clock timeout;
- process-count limits;
- network disabled by default;
- read-only base filesystem;
- temporary working directory;
- output-size limits;
- approved language runtimes;
- dependency restrictions;
- container or VM isolation;
- cleanup after execution;
- audit logging.

### Security acceptance criteria

- host filesystem is inaccessible;
- private network services are inaccessible;
- cloud metadata endpoints are inaccessible;
- resource exhaustion is contained;
- fork-bomb tests are contained;
- timeout tests pass;
- malicious file-access tests fail safely;
- sandbox images are versioned and scanned;
- security review is approved.

Untrusted code must never execute directly inside the API process.

## 15. Workstream 11: Privacy and governance

### Required controls

Implement and verify:

- consent versioning;
- consent withdrawal;
- linked-record discovery;
- deletion or approved anonymization;
- retention schedules;
- automatic retention enforcement;
- encrypted storage;
- encrypted backups;
- least-privilege access;
- audit logging;
- dataset export approval;
- incident response;
- participant information process.

### Acceptance criteria

- withdrawal workflow passes end-to-end testing;
- retention jobs are tested;
- encryption controls are documented;
- authorized roles are defined;
- production secrets are managed securely;
- customer privacy approval is recorded.

## 16. Workstream 12: Fairness evaluation

### Objective

Identify material performance differences across relevant groups.

Potential analysis dimensions include:

- programming experience;
- input language;
- problem category;
- modality availability;
- speech usage;
- retry status.

### Requirements

- only collect attributes with an approved purpose;
- maintain minimum subgroup sizes;
- avoid publishing identifiable subgroup data;
- report uncertainty;
- investigate large disparities;
- document mitigation decisions.

## 17. Workstream 13: Latency and resource evaluation

Measure:

- API response latency;
- diagnosis latency;
- model inference latency;
- database query latency;
- export latency;
- CPU usage;
- memory usage;
- concurrent-user behavior;
- failure and fallback rates.

### Deliverables

- load-test configuration;
- latency percentile report;
- resource report;
- capacity recommendation;
- operational limits;
- fallback and timeout policy.

## 18. Workstream 14: Learning-effectiveness study

### Objective

Determine whether diagnosis and interventions improve student outcomes.

Potential measures include:

- retry correctness;
- misconception resolution;
- time to successful correction;
- hint usage;
- diagnostic-question completion;
- teacher-rated intervention usefulness;
- student-rated usefulness;
- delayed retention where feasible.

The study design must distinguish system usability from learning improvement.

## 19. Workstream 15: Final deliverables

Phase 2 should produce:

- approved taxonomy;
- annotation handbook;
- pilot report;
- versioned research dataset;
- final dataset card;
- final model card;
- statistical evaluation report;
- faculty agreement report;
- calibration report;
- fairness report;
- performance and resource report;
- privacy and security report;
- OCR report, if applicable;
- sandbox security report, if applicable;
- technical report;
- customer execution guide;
- final presentation;
- research paper draft;
- poster.

## 20. Customer responsibilities

The customer should provide or approve:

- faculty reviewers;
- student recruitment;
- institutional permissions;
- consent language;
- data ownership;
- retention policy;
- deployment environment;
- OCR requirement;
- code-execution requirement;
- supported languages;
- success criteria;
- pilot schedule;
- final acceptance authority.

Delays in these dependencies will affect the Phase 2 schedule.

## 21. Project-team responsibilities

The project team should:

- maintain the application;
- support controlled deployment;
- prepare annotation tools;
- implement approved controls;
- version datasets and models;
- preserve reproducibility;
- calculate agreed metrics;
- report failed targets honestly;
- maintain limitations documentation;
- prepare final deliverables.

## 22. Phase gates

### Gate 1: Protocol approval

Required:

- taxonomy draft;
- annotation guide;
- consent material;
- retention policy;
- pilot plan.

### Gate 2: Pilot readiness

Required:

- controlled deployment;
- CI passing;
- security checks;
- withdrawal procedure;
- faculty onboarding.

### Gate 3: Dataset readiness

Required:

- minimum eligible records;
- completed review;
- adjudication;
- de-identification;
- quality report.

### Gate 4: Evaluation readiness

Required:

- frozen splits;
- frozen metrics;
- reproducible baselines;
- approved test procedure.

### Gate 5: Research acceptance

Required:

- final metrics;
- agreement report;
- calibration report;
- fairness analysis;
- customer review.

### Gate 6: Production decision

Required:

- security approval;
- privacy approval;
- capacity report;
- operational ownership;
- deployment and rollback plan.

## 23. Definition of done

Phase 2 is complete only when:

- 300–500 genuine consented attempts are collected;
- two faculty reviewers complete validation;
- the student pilot is completed;
- student-grouped splits are frozen;
- agreed metrics are calculated;
- results are reproducible;
- limitations are updated;
- required privacy controls are implemented;
- security decisions are documented;
- final deliverables are approved by the customer.

Meeting engineering milestones alone is not sufficient for Phase 2 completion.

## 24. Current recommendation

Proceed with customer review of the Phase 1 engineering MVP.

Use customer feedback to finalize:

- Phase 2 scope;
- participant access;
- faculty availability;
- OCR decision;
- sandbox decision;
- privacy requirements;
- research timeline.

The defensible current statement is:

> The engineering MVP is ready for customer evaluation. Research-scale
> validation and advanced production controls are formally planned as Phase 2
> and depend on customer-approved participants, policies, and acceptance
> criteria.

## 25. Related documents

- `docs/evaluation/EVALUATION_REPORT.md`
- `docs/model/MODEL_CARD.md`
- `docs/dataset/DATASET_CARD.md`
- `docs/KNOWN_LIMITATIONS.md`
- `README.md`