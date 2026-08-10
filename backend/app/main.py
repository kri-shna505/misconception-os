from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.attempt_routes import router as attempts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.diagnosis_routes import router as diagnoses_router
from app.api.routes.health_routes import router as health_router
from app.api.routes.intervention_routes import (
    router as interventions_router,
)
from app.api.routes.problem_routes import router as problems_router
from app.api.routes.student_routes import router as student_router
from app.api.routes.teacher_review_routes import (
    router as teacher_reviews_router,
)
from app.api.routes.teacher_routes import router as teacher_router


app = FastAPI(
    title="MisconceptionOS API",
    description=(
        "Backend API for the MisconceptionOS DSA diagnostic tutor, including "
        "student submissions, evidence-backed misconception diagnosis, "
        "progressive hints, diagnostic questions, retry attempts, learning "
        "history, teacher analytics, authentication, and teacher review "
        "workflows."
    ),
    version="0.5.0",
    openapi_tags=[
        {
            "name": "System",
            "description": (
                "API status, metadata, and root information."
            ),
        },
        {
            "name": "Health",
            "description": (
                "Backend application and database health checks."
            ),
        },
        {
            "name": "Authentication",
            "description": (
                "Teacher login, authenticated-user lookup, logout, "
                "and password-management endpoints."
            ),
        },
        {
            "name": "Students",
            "description": (
                "Pseudonymous student-session operations."
            ),
        },
        {
            "name": "Problems",
            "description": (
                "DSA problem-bank operations."
            ),
        },
        {
            "name": "Attempts",
            "description": (
                "Student-attempt submission and retrieval."
            ),
        },
        {
            "name": "Diagnoses",
            "description": (
                "Evidence extraction and rule-based misconception diagnosis."
            ),
        },
        {
            "name": "Interventions",
            "description": (
                "Progressive hints, diagnostic questions, diagnostic "
                "responses, retry attempts, misconception evolution, "
                "and student learning-history operations."
            ),
        },
        {
            "name": "Teacher",
            "description": (
                "Teacher dashboard, attempt review, student history, "
                "problem analytics, and misconception analytics endpoints."
            ),
        },
        {
            "name": "Teacher Reviews",
            "description": (
                "Protected teacher-review queue, draft, acceptance, "
                "override, finalization, and reopen operations."
            ),
        },
    ],
)


# Development CORS configuration.
#
# Allows the Vite frontend to run on localhost or 127.0.0.1 using any
# development port, such as 5173, 5174, 5175, and so on.
#
# This permissive localhost configuration is for development only.
# Production deployment must use an explicit origin allow-list.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^http://(localhost|127\.0\.0\.1):\d+$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    tags=["System"],
    summary="Get API information",
    description=(
        "Return API metadata and selected endpoint locations."
    ),
)
def root() -> dict[str, str]:
    return {
        "name": "MisconceptionOS API",
        "version": app.version,
        "status": "running",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/api/health",
        "auth_login": "/api/auth/login",
        "auth_me": "/api/auth/me",
        "teacher_dashboard": "/api/teacher/dashboard",
        "teacher_reviews": "/api/teacher/reviews",
        "interventions": "/api/interventions",
        "learning_history": (
            "/api/interventions/students/"
            "{student_alias_id}/learning-history"
        ),
    }


app.include_router(
    health_router,
    prefix="/api",
)

app.include_router(
    auth_router,
    prefix="/api",
)

app.include_router(
    student_router,
    prefix="/api",
)

app.include_router(
    problems_router,
    prefix="/api",
)

app.include_router(
    attempts_router,
    prefix="/api",
)

app.include_router(
    diagnoses_router,
    prefix="/api",
)

app.include_router(
    interventions_router,
    prefix="/api",
)

app.include_router(
    teacher_router,
    prefix="/api",
)

app.include_router(
    teacher_reviews_router,
    prefix="/api",
)