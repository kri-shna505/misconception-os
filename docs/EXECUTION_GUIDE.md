# Misconception OS Execution Guide

**Document status:** Phase 1 customer execution guide
**Release position:** Validated engineering MVP
**Current milestone:** Sprint 11 — hybrid rule-plus-ML diagnosis with automatic rule-only fallback

## 1. Purpose

This guide explains how to install, configure, start, validate, and demonstrate
the Phase 1 Misconception OS engineering MVP.

The application supports two principal workflows:

1. student attempt submission and misconception diagnosis;
2. teacher review, correction, and reviewed-dataset export.

This guide validates executable engineering behavior. It does not claim that
the research targets in the original proposal have been achieved. Research
validation is defined separately in
[`NEXT_PHASE_VALIDATION.md`](NEXT_PHASE_VALIDATION.md).

## 2. Implemented Phase 1 capabilities

The current release includes:

- anonymous student aliases and attempt tracking;
- structured programming problems;
- final-answer, written-reasoning, source-code, and speech-transcript inputs;
- English and Telugu-aware normalized reasoning;
- deterministic evidence extraction;
- problem-specific rule-based diagnosis;
- baseline logistic-regression inference;
- hybrid rule-plus-ML fusion;
- automatic rule-only fallback;
- diagnosis confidence and provenance;
- progressive hints and diagnostic questions;
- retry and intervention history;
- teacher review workflows;
- teacher-reviewed dataset export;
- PostgreSQL persistence;
- Alembic database migrations;
- backend and frontend automated CI.

## 3. Important limitations

The Phase 1 release does not currently provide:

- handwriting OCR;
- secure execution of submitted source code;
- a restricted code-execution sandbox;
- research-grade evaluation using 300–500 genuine labelled attempts;
- faculty-validated taxonomy results;
- a 20-student institutional pilot;
- validated Macro F1, Cohen's kappa, or calibration targets;
- transformer or true multimodal neural baselines.

Source code entered by students is treated as text evidence. It must not be
described as securely executed code.

See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) for the complete disclosure.

## 4. Repository layout

```text
misconceptionos/
├── .github/workflows/
├── backend/
│   ├── alembic/
│   ├── app/
│   ├── ml/
│   ├── tests/
│   ├── alembic.ini
│   └── requirements.txt
├── docs/
├── frontend/
├── .env.example
├── README.md
└── docker-compose.yml
```

## 5. Prerequisites

Install the following software before setup:

- Git;
- Python 3.12;
- Node.js 24 or a compatible current Node.js release;
- npm 11 or a compatible npm release;
- Docker Desktop;
- PostgreSQL 16 through Docker Compose;
- PowerShell 7 or Windows PowerShell.

Confirm the primary tools:

```powershell
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

## 6. Clone and enter the repository

```powershell
git clone https://github.com/axion-5025/misconceptionos.git
cd misconceptionos
git switch main
git pull --ff-only origin main
```

The repository is private. The customer must use an authorized GitHub account
or an approved source archive.

## 7. Environment configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

The local PostgreSQL configuration used by the project is:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/misconceptionos
BACKEND_HOST=localhost
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

Add a development JWT secret containing at least 32 characters:

```dotenv
JWT_SECRET_KEY=replace-this-with-a-local-secret-containing-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

For hybrid ML diagnosis:

```dotenv
ML_DIAGNOSIS_ENABLED=true
ML_MODEL_CACHE_ENABLED=true
```

Do not commit `.env`. Secrets shown in documentation are examples and must not
be reused in a deployed environment.

## 8. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d postgres
docker compose ps
```

Expected result:

- the PostgreSQL container is running;
- host port `5433` maps to container port `5432`;
- database name is `misconceptionos`.

If the container already exists:

```powershell
docker compose restart postgres
docker compose ps
```

## 9. Create the Python virtual environment

The supported local virtual environment is at repository root:

```powershell
python -m venv .venv
```

Activate it:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

Do not create or commit `backend/venv`. Python environments and generated
cache files are excluded through the root `.gitignore`.

## 10. Apply database migrations

Move into the backend directory:

```powershell
cd backend
```

Apply all migrations:

```powershell
python -m alembic upgrade head
```

Verify the database revision:

```powershell
python -m alembic current
python -m alembic heads
```

The current revision and head must match. For the Sprint 11 baseline, the
migration lineage includes revision:

```text
da7793312fb1
```

Return to the repository root when required:

```powershell
cd ..
```

## 11. Start the backend API

Open terminal 1:

```powershell
cd C:\misconceptionos
& .\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected backend URL:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Keep this terminal running.

## 12. Install and start the frontend

Open terminal 2:

```powershell
cd C:\misconceptionos
npm --prefix frontend ci
npm --prefix frontend run dev
```

Expected frontend URL:

```text
http://localhost:5173
```

Keep this terminal running.

If dependencies are already installed and unchanged, the frontend may be
started with:

```powershell
npm --prefix frontend run dev
```

## 13. Verify ML availability

With `ML_DIAGNOSIS_ENABLED=true`, run from `backend`:

```powershell
python -c "from app.core.config import settings; print({'enabled': settings.ML_DIAGNOSIS_ENABLED, 'model_path': settings.ML_MODEL_PATH, 'cache': settings.ML_MODEL_CACHE_ENABLED})"
```

Then verify service availability:

```powershell
python -c "from app.services.ml_diagnosis_service import ml_diagnosis_available; print(ml_diagnosis_available().to_dict())"
```

Expected engineering result:

- ML diagnosis is enabled;
- the persisted model artifact is discoverable or the service reports its
  availability;
- failure to load ML does not prevent rule-based diagnosis.

## 14. Verify automatic rule-only fallback

Temporarily disable ML in the current PowerShell process:

```powershell
$env:ML_DIAGNOSIS_ENABLED="false"
```

Run backend tests:

```powershell
cd C:\misconceptionos\backend
python -m pytest -q
```

Remove the temporary override:

```powershell
Remove-Item Env:ML_DIAGNOSIS_ENABLED
```

The diagnosis workflow must remain operational through deterministic
rule-only behavior.

## 15. Student workflow demonstration

Use a clean browser session for the recording.

### 15.1 Open the student interface

1. Open `http://localhost:5173`.
2. Select the student workflow.
3. Create or enter an anonymous student alias.
4. Confirm that no unnecessary personally identifying information is entered.

### 15.2 Select a programming problem

1. Open the available problem list.
2. Select a problem with a known misconception mapping.
3. Display the problem statement and expected response fields.

### 15.3 Submit multimodal text evidence

Enter:

- a final answer;
- written reasoning;
- source code;
- an optional speech transcript;
- the selected input or programming language when available.

The current system accepts a speech transcript as evidence. The recording
must not claim that arbitrary live audio is processed by a research-grade
multimodal neural encoder.

### 15.4 Show the diagnosis

Submit the attempt and display:

- diagnosis state;
- primary misconception;
- confidence;
- evidence or explanation;
- intervention type;
- model or prediction provenance when exposed by the interface.

Explain that the result may originate from:

- deterministic rules;
- hybrid rule-plus-ML fusion;
- automatic rule-only fallback.

### 15.5 Show intervention and retry

1. Display the generated hint, diagnostic question, or clarification request.
2. Submit a revised response when the interface permits.
3. Show that the original attempt and follow-up diagnosis remain traceable.
4. Demonstrate that the system supports iterative learning rather than only
   marking an answer correct or incorrect.

## 16. Teacher workflow demonstration

Use an authorized teacher account or the configured demonstration teacher
workflow.

### 16.1 Open the teacher dashboard

1. Open the teacher interface.
2. Display the list of student attempts.
3. Show pending, in-review, and reviewed states when data is available.
4. Open one attempt without exposing unnecessary personal information.

### 16.2 Review diagnosis evidence

Display:

- student answer;
- written reasoning;
- source-code text;
- speech transcript when present;
- predicted misconception;
- confidence and provenance;
- rule and ML component information when exposed.

### 16.3 Correct or confirm the diagnosis

1. Confirm the predicted misconception or select a corrected label.
2. Add review notes where supported.
3. Mark the record as reviewed.
4. Show that teacher review does not overwrite the immutable original
   diagnosis record.

### 16.4 Export the reviewed dataset

Demonstrate the teacher-reviewed export workflow.

Expected engineering outputs include:

```text
backend/ml/data/exports/teacher_reviewed_dataset.csv
backend/ml/data/exports/teacher_reviewed_dataset.jsonl
```

The current repository evidence contains only a small reviewed sample. It
must not be presented as the proposal's required 300–500 genuine labelled
attempts.

## 17. Backend validation

Activate the root virtual environment and run from `backend`:

```powershell
cd C:\misconceptionos
& .\.venv\Scripts\Activate.ps1
cd backend
python -m alembic upgrade head
python -m pytest -q
```

Validated Phase 1 baseline:

```text
340 passed
```

Deprecation warnings may still be reported. Warnings do not invalidate the
passing test result, but they remain technical debt and must not be hidden.

## 18. Frontend validation

From repository root:

```powershell
cd C:\misconceptionos
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run build
```

Validated Phase 1 baseline:

- frontend installation succeeds;
- lint completes with zero errors;
- the production build succeeds;
- lint warnings may remain and should be recorded honestly.

## 19. GitHub CI validation

The repository contains:

```text
.github/workflows/backend-ci.yml
.github/workflows/frontend-ci.yml
```

Check recent workflow runs:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list --branch main --limit 5
```

Both Backend CI and Frontend CI should show successful runs for the current
main branch commit.

## 20. End-to-end demo evidence checklist

Capture the following evidence before customer delivery:

| Evidence | Required result |
|---|---|
| Repository state | Clean `main` branch |
| PostgreSQL | Container running |
| Alembic | Current revision equals head |
| Backend tests | 340 tests pass |
| Frontend lint | Zero errors |
| Frontend build | Production build passes |
| Backend startup | API starts without fatal error |
| Frontend startup | UI loads at port 5173 |
| Student submission | Attempt saved successfully |
| Diagnosis | State, label, confidence, and intervention shown |
| Retry workflow | Follow-up attempt or intervention demonstrated |
| Teacher dashboard | Attempt visible for review |
| Teacher validation | Diagnosis confirmed or corrected |
| Dataset export | Reviewed export generated |
| ML enabled mode | Hybrid path demonstrated when available |
| ML disabled mode | Rule-only fallback remains operational |
| CI | Backend and frontend workflows pass |

Record the date, commit hash, operator, environment, and result for every
captured item.

## 21. Recommended recording sequence

### Video A — Student workflow

Target duration: 4–6 minutes.

1. Show project title and current Phase 1 positioning.
2. Start with the student interface.
3. Enter an anonymous alias.
4. Select a programming problem.
5. Enter final answer, reasoning, and source code.
6. Add speech transcript evidence when useful.
7. Submit the attempt.
8. Explain diagnosis state, misconception, confidence, and provenance.
9. Show the generated intervention.
10. Demonstrate retry or follow-up behavior.
11. End with a short statement of limitations.

### Video B — Teacher workflow

Target duration: 4–6 minutes.

1. Open the teacher dashboard.
2. Show attempt status counts.
3. Open the student attempt created in Video A.
4. Review multimodal evidence.
5. Review diagnosis label, confidence, and provenance.
6. Confirm or correct the label.
7. Mark the attempt as reviewed.
8. Demonstrate dataset export.
9. Explain that the reviewed sample is engineering evidence, not yet the
   complete research dataset.
10. End with the Phase 2 validation plan.

## 22. Troubleshooting

### Backend imports fail with `No module named 'app'`

Cause: tests or backend commands were executed from repository root.

Fix:

```powershell
cd C:\misconceptionos\backend
python -m pytest -q
```

### Frontend cannot find `package.json`

Cause: `npm --prefix frontend` was executed while already inside the
`frontend` directory.

From repository root use:

```powershell
npm --prefix frontend run build
```

From inside `frontend` use:

```powershell
npm run build
```

Do not combine both forms.

### PostgreSQL connection fails

Check the container:

```powershell
cd C:\misconceptionos
docker compose ps
docker compose logs postgres
```

Confirm that the application uses host port `5433`, not `5432`.

### Alembic reports multiple heads

Run:

```powershell
cd C:\misconceptionos\backend
python -m alembic heads
python -m alembic history
```

Do not create an additional migration until the migration lineage is
understood and reconciled.

### ML reports unavailable

Check:

```powershell
cd C:\misconceptionos\backend
python -c "from app.services.ml_diagnosis_service import ml_diagnosis_available; print(ml_diagnosis_available().to_dict())"
```

Confirm:

- `ML_DIAGNOSIS_ENABLED=true`;
- the model artifact exists;
- required Python packages are installed.

If ML remains unavailable, the application should continue with rule-only
fallback. Do not claim hybrid inference if the returned prediction source
shows rule-only behavior.

### Port is already in use

Inspect ports:

```powershell
Get-NetTCPConnection -LocalPort 5173,8000,5433 -ErrorAction SilentlyContinue
```

Stop the stale process or start the affected service on an approved alternate
port and update the corresponding configuration.

## 23. Safe shutdown

Stop frontend and backend terminals using `Ctrl+C`.

Stop PostgreSQL:

```powershell
cd C:\misconceptionos
docker compose down
```

To retain database data, do not add `--volumes`.

## 24. Customer delivery package

The Phase 1 customer package should contain:

- GitHub repository link;
- student workflow video;
- teacher workflow video;
- execution guide;
- evaluation report;
- model card;
- dataset card;
- known-limitations document;
- next-phase validation plan;
- presentation deck;
- recorded validation evidence.

## 25. Related documents

- [`README.md`](../README.md)
- [`EVALUATION_REPORT.md`](evaluation/EVALUATION_REPORT.md)
- [`MODEL_CARD.md`](model/MODEL_CARD.md)
- [`DATASET_CARD.md`](dataset/DATASET_CARD.md)
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)
- [`NEXT_PHASE_VALIDATION.md`](NEXT_PHASE_VALIDATION.md)

## 26. Delivery statement

Phase 1 should be described as:

> A validated engineering MVP covering the core student and teacher workflows,
> deterministic and baseline ML diagnosis, safe fallback behavior, persistence,
> migrations, automated tests, CI, and customer-facing technical documentation.

It must not be described as:

> A fully research-validated multimodal AI system satisfying every quantitative,
> participant, privacy, security, and publication requirement in the original
> proposal.

The remaining research validation is explicitly assigned to Phase 2.