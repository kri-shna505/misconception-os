from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables
    and the backend .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = (
        "postgresql://postgres:postgres@127.0.0.1:5433/"
        "misconceptionos"
    )

    JWT_SECRET_KEY: str = Field(
        default=(
            "-xSP3-sFZ0OvtwaNxS2X3i9ZsVdhnWi715VIiIgf62FfiV8ZIc5v5p_CKJEudTb6"
        ),
        min_length=32,
    )

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Sprint 11 hybrid diagnosis configuration.
    #
    # ML is intentionally disabled by default. This preserves the existing
    # deterministic rule-only behavior unless the deployment explicitly opts
    # into hybrid inference.
    ML_DIAGNOSIS_ENABLED: bool = False

    # Leave this unset to use the default artifact path configured by the
    # inference module. A deployment may override it through the backend .env.
    ML_MODEL_PATH: str | None = None

    # Reuse the deserialized model between requests in normal application
    # operation. Tests may override this setting when isolation is required.
    ML_MODEL_CACHE_ENABLED: bool = True

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(
        cls,
        value: str,
    ) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                "DATABASE_URL cannot be empty."
            )

        return normalized_value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(
        cls,
        value: str,
    ) -> str:
        normalized_value = value.strip()

        if len(normalized_value) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must contain at least "
                "32 characters."
            )

        return normalized_value

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(
        cls,
        value: str,
    ) -> str:
        normalized_value = value.strip().upper()

        allowed_algorithms = {
            "HS256",
            "HS384",
            "HS512",
        }

        if normalized_value not in allowed_algorithms:
            raise ValueError(
                "JWT_ALGORITHM must be one of: "
                "HS256, HS384, HS512."
            )

        return normalized_value

    @field_validator(
        "ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    @classmethod
    def validate_access_token_expiry(
        cls,
        value: int,
    ) -> int:
        if value <= 0:
            raise ValueError(
                "ACCESS_TOKEN_EXPIRE_MINUTES must "
                "be greater than zero."
            )

        if value > 1440:
            raise ValueError(
                "ACCESS_TOKEN_EXPIRE_MINUTES must "
                "not exceed 1440 minutes."
            )

        return value

    @field_validator(
        "ML_MODEL_PATH",
        mode="before",
    )
    @classmethod
    def normalize_ml_model_path(
        cls,
        value: object,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = str(value).strip()

        return normalized_value or None


settings = Settings()