# Misconception OS

[![Backend CI](https://github.com/axion-5025/misconceptions/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/axion-5025/misconceptions/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/axion-5025/misconceptions/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/axion-5025/misconceptions/actions/workflows/frontend-ci.yml)

An AI-assisted learning system that detects programming misconceptions from student answers, written reasoning, source code, and speech evidence.

**Current milestone:** Sprint 11 - hybrid rule and machine-learning diagnosis with automatic rule-only fallback.

Misconception OS does more than mark an answer correct or incorrect. It gathers multimodal evidence, identifies the likely conceptual misunderstanding, records confidence and provenance, and selects an appropriate intervention such as a hint, diagnostic question, clarification request, or no action.

## Implemented system

- Anonymous student aliases and attempt tracking
- Structured programming problems and misconception taxonomy
- Final-answer, written-reasoning, source-code, and speech inputs
- Normalized multilingual reasoning with Telugu support
- Deterministic evidence extraction and rule-based diagnosis
- Problem-specific misconception allowlists
- Diagnosis states: `confident`, `possible`, `insufficient`, and `no_misconception`
- Progressive hints and targeted diagnostic questions
- Immutable follow-up diagnoses after student clarification
- Retry chains and intervention history
- Teacher review and reviewed-dataset export
- Reproducible baseline ML training
- Persisted logistic-regression model and evaluation metrics
- Rule-plus-ML hybrid fusion
- Runtime ML feature and version provenance
- Automatic fallback when ML is disabled, missing, or fails
- PostgreSQL persistence and Alembic migrations
- React teacher and student workflows
- FastAPI backend with interactive API documentation
- 340 backend tests
- Frontend lint and production-build validation

## Diagnosis pipeline

```mermaid
flowchart TD
    A["Student attempt"] --> B["Evidence extraction"]
    B --> C["Rule diagnosis"]
    C --> D{"ML enabled and available?"}
    D -- "No" --> E["Rule-only result"]
    D -- "Yes" --> F["ML inference"]
    F --> G["Rule and ML fusion"]
    F -. "Failure" .-> E
    G --> H["Persist diagnosis and provenance"]
    E --> H
    H --> I["Hint, question, clarification, or no action"]
```

The rule engine remains the safety path. Missing artifacts, availability failures, inference errors, and fusion errors automatically fall back to the existing deterministic result. Database failures are not hidden: persistence errors still roll back and surface normally.

## Misconception coverage

| Code | Misconception |
|---|---|
| `M1` | Binary search used on unsorted data |
| `M2` | Missing or incorrect recursion base case |
| `M3` | Recursive call does not reduce the problem size |
| `M4` | Pass-by-value versus pass-by-reference confusion |
| `M5` | Stack versus heap confusion |

Each problem is restricted to its configured misconception allowlist, preventing cross-topic diagnoses.

## Diagnosis states and interventions

| State | Confidence contract | Intervention |
|---|---:|---|
| `confident` | `>= 0.75` | Show a progressive hint |
| `possible` | `>= 0.45` and `< 0.75` | Ask a diagnostic question |
| `insufficient` | `< 0.45` | Ask for clarification |
| `no_misconception` | `>= 0.75` | No intervention |

## Hybrid ML layer

Sprint 11 adds an auditable engineering ML baseline around the deterministic diagnosis system:

- Teacher-reviewed diagnosis export to CSV and JSONL
- Label mapping and feature construction
- Deterministic smoke-dataset generation
- Baseline logistic-regression training
- Persisted model artifact and metrics
- Cached runtime inference
- Weighted rule-plus-ML fusion
- Agreement and component-score tracking
- Feature and model version metadata
- Safe rule-only fallback

The baseline is not presented as a research-final classifier. It supports controlled iteration without weakening the production safety path.

## Architecture

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React 19, TypeScript, Vite | Student attempts, interventions, retries, and teacher review |
| API | FastAPI | Validation, authentication, and diagnosis endpoints |
| Rules | Python evidence extractor and rule detector | Deterministic misconception signals |
| ML | scikit-learn and joblib | Feature building, inference, and persisted baseline model |
| Fusion | Python hybrid decision layer | Rule and ML score reconciliation |
| Database | PostgreSQL 16 | Attempts, diagnoses, evidence, reviews, and interventions |
| Migrations | Alembic | Versioned schema evolution |
| Testing | pytest, Oxlint, TypeScript, Vite | Backend and frontend quality gates |
| CI | GitHub Actions | Automated migrations, tests, lint, and builds |

## Repository structure

```text
misconceptions/
|-- .github/
|   `-- workflows/
|       |-- backend-ci.yml
|       `-- frontend-ci.yml
|-- backend/
|   |-- alembic/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- ml/
|   |   |-- models/
|   |   |-- schemas/
|   |   `-- services/
|   |-- ml/
|   |   |-- data/exports/
|   |   |-- models/baseline/
|   |   `-- training/
|   `-- tests/
|-- frontend/
|   |-- public/
|   `-- src/
|-- .env.example
|-- docker-compose.yml
`-- README.md
```

## Requirements

- Python 3.12
- Node.js 24
- npm 11
- Docker Desktop
- PostgreSQL 16 through Docker Compose

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/axion-5025/misconceptions.git
cd misconceptions
```

### 2. Start PostgreSQL

```bash
docker compose up -d postgres
```

PostgreSQL is mapped to host port `5433`.

### 3. Configure the backend

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/misconceptionos
JWT_SECRET_KEY=replace-this-with-a-random-secret-containing-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ML_DIAGNOSIS_ENABLED=true
ML_MODEL_CACHE_ENABLED=true
```

Never commit `backend/.env`.

### 4. Install and migrate the backend

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
cd backend
python -m alembic upgrade head
```

### 5. Run the backend

From `backend/`:

```powershell
python -m uvicorn app.main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

### 6. Install and run the frontend

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend: <http://localhost:5173>

## Validation

### Backend

Run from `backend/`:

```powershell
$env:ML_DIAGNOSIS_ENABLED="false"
python -m alembic upgrade head
python -m pytest -q
Remove-Item Env:ML_DIAGNOSIS_ENABLED
```

Expected result: `340 passed`.

### Frontend

Run from `frontend/`:

```powershell
npm ci
npm run lint
npm run build
```

The current lint configuration allows warnings but rejects errors.

## ML operations

Run these commands from `backend/`.

Check model availability:

```powershell
python -c "from app.services.ml_diagnosis_service import ml_diagnosis_available; print(ml_diagnosis_available().to_dict())"
```

Build the smoke dataset:

```powershell
python ml/training/build_smoke_dataset.py
```

Train the baseline model:

```powershell
python ml/training/train_baseline.py
```

Training outputs are stored under `backend/ml/models/baseline/`.

## Continuous integration

### Backend CI

When backend files change, GitHub Actions starts PostgreSQL 16, installs Python 3.12 dependencies, applies Alembic migrations, verifies the migration revision, and runs the backend test suite with ML disabled to guarantee rule-path stability.

### Frontend CI

When frontend files change, GitHub Actions installs locked dependencies, runs Oxlint, performs TypeScript compilation, and builds the Vite production bundle.

Both workflows support manual execution from the GitHub Actions page.

## Data and privacy

- Student identity is represented through aliases.
- Diagnosis evidence and model provenance are stored for auditability.
- Teacher-reviewed examples can be exported for controlled model training.
- Speech retention is represented explicitly rather than assumed.
- Local `.env` files are ignored and must never be committed.
- The included ML dataset is a small engineering dataset, not a production-scale research corpus.

## Known limitations

- The current misconception taxonomy is intentionally small.
- The baseline ML model is trained on limited reviewed data.
- ML confidence is not research-grade calibration.
- Frontend lint currently reports warnings that should be reduced over time.
- Production deployment, monitoring, and large-scale evaluation remain separate operational work.

## Project status

Sprint 11 is complete.

- 340 backend tests passed
- Frontend lint completed with 0 errors
- Frontend production build passed
- Alembic database revision is at head
- Persisted ML artifact is available
- Live hybrid inference smoke test passed
- Explicit rule-only regression mode passed
- Hybrid diagnosis is merged into `main`

## Author

Developed by [axion-5025](https://github.com/axion-5025).
