import tomllib
from functools import cache
from pathlib import Path
from typing import Annotated, Any, cast

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .enums.environment import Environment

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/
_PYPROJECT_PATH = _PROJECT_ROOT / "pyproject.toml"
_BYTES_PER_MB = 1024 * 1024


def _get_project_metadata() -> dict[str, Any]:
    if _PYPROJECT_PATH.exists():
        with _PYPROJECT_PATH.open("rb") as file:
            return cast(dict[str, Any], tomllib.load(file).get("project", {}))

    return {
        "name": "RAG-backend",
        "version": "0.0.0",
        "description": "Fallback application description",
    }


_PROJECT_METADATA = _get_project_metadata()


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # ------------ Application ------------
    APP_NAME: str = _PROJECT_METADATA.get("name", "RAG Backend")
    APP_VERSION: str = _PROJECT_METADATA.get("version", "0.1.0")
    APP_DESCRIPTION: str = _PROJECT_METADATA.get("description", "")
    ENVIRONMENT: Environment = Environment.LOCAL
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/rag.db"

    # ------------ Storage ------------
    MAX_FILE_SIZE_MB: Annotated[int, Field(gt=0)] = 50
    UPLOAD_DIR: Path = _PROJECT_ROOT / "data" / "uploads"

    # ------------ Upload limits ------------
    MAX_FILES_PER_REQUEST: Annotated[int, Field(gt=0)] = 10
    UPLOAD_RATE_LIMIT: str = "10/hour"
    UPLOAD_CONCURRENCY: Annotated[int, Field(gt=0)] = 4

    # ------------ Chunking ------------
    CHUNK_SIZE_TOKENS: Annotated[int, Field(gt=0)] = 512
    CHUNK_OVERLAP_TOKENS: Annotated[int, Field(ge=0)] = 64

    # ------------ Embeddings & Vector Store ------------
    QDRANT_URL: str = "http://localhost:6333"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_BATCH_SIZE: Annotated[int, Field(gt=0)] = 16

    # ------------ Retrieval ------------
    RETRIEVAL_TOP_K: Annotated[int, Field(gt=0)] = 8
    RETRIEVAL_HYBRID: bool = True

    # ------------ Memory ------------
    MEMORY_SHORT_TERM_N: int = 10
    MEMORY_SUMMARY_EVERY_K: int = 6

    # ------------ LLM Generation ------------
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_API_KEY: str = "sk-dummy"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_CONTEXT_TOKEN_BUDGET: int = 6000
    LLM_TIMEOUT_S: int = 60

    @model_validator(mode="after")
    def _ensure_upload_dir(self) -> "Settings":
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * _BYTES_PER_MB


@cache
def get_settings() -> Settings:
    """Return the application-wide settings instance."""
    return Settings()
