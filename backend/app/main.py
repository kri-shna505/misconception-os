from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.attempt_routes import router as attempts_router
from app.api.routes.diagnosis_routes import router as diagnoses_router
from app.api.routes.health_routes import router as health_router
from app.api.routes.problem_routes import router as problems_router
from app.api.routes.student_routes import router as student_router


app = FastAPI(
    title="MisconceptionOS API",
    description="Backend API for the MisconceptionOS DSA diagnostic tutor.",
    version="0.1.0",
)

# Development CORS configuration.
#
# Allows the Vite frontend to run on localhost or 127.0.0.1 using any
# development port, such as 5173, 5174, 5175, and so on.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "name": "MisconceptionOS API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }


app.include_router(
    health_router,
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