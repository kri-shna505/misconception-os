from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5433/misconceptionos"

    class Config:
        env_file = ".env"


settings = Settings()