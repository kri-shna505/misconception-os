from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health_routes import router as health_router
from app.api.routes.problem_routes import router as problem_router
from app.api.routes.student_routes import router as student_router
from app.api.routes.attempt_routes import router as attempt_router

app = FastAPI(
    title="MisconceptionOS API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(student_router, prefix="/api")
app.include_router(problem_router, prefix="/api")
app.include_router(attempt_router, prefix="/api")