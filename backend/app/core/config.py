from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://ava:ava@localhost:5432/ava"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # Ollama
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_chat_model: str = "mistral"
    ollama_router_model: str = "phi3:mini"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
