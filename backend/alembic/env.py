from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base

# Import every model explicitly so Alembic can discover all tables,
# columns, constraints, foreign keys, and indexes during autogenerate.
from app.models.attempt import Attempt  # noqa: F401
from app.models.diagnosis import Diagnosis  # noqa: F401
from app.models.diagnosis_alternative import DiagnosisAlternative  # noqa: F401
from app.models.diagnosis_evidence import DiagnosisEvidence  # noqa: F401
from app.models.diagnostic_question import DiagnosticQuestion  # noqa: F401
from app.models.hint_template import HintTemplate  # noqa: F401
from app.models.misconception import Misconception  # noqa: F401
from app.models.problem import Problem  # noqa: F401
from app.models.problem_misconception import ProblemMisconception  # noqa: F401
from app.models.student_alias import StudentAlias  # noqa: F401
from app.models.teacher_review import TeacherReview  # noqa: F401
from app.models.user import User  # noqa: F401


config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL,
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without creating a live database connection.

    Alembic emits SQL statements using the configured database URL.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations using a live database connection.
    """

    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()