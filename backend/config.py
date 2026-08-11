"""
Central configuration module.
All settings are loaded from environment variables via .env file.
"""
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: str = "openai"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-02-01"

    # --- Embeddings ---
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "openai"

    # --- Database ---
    database_url: str = f"sqlite:///{PROJECT_ROOT}/artifacts/incidents.db"

    # --- Security ---
    secret_key: str = "change-this-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # --- ChromaDB ---
    chroma_path: str = str(PROJECT_ROOT / "artifacts" / "chroma_db")
    chroma_collection_name: str = "incident_knowledge"

    # --- Knowledge Base ---
    knowledge_base_path: str = str(PROJECT_ROOT / "data" / "knowledge_base")

    # --- Admin Setup ---
    admin_username: str = "admin"
    admin_email: str = "admin@company.com"

    # --- Application ---
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_port: int = 8501
    log_level: str = "INFO"

    # --- DeepEval ---
    deepeval_api_key: str = ""

    @property
    def absolute_chroma_path(self) -> str:
        """Return absolute path for ChromaDB."""
        p = Path(self.chroma_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    @property
    def absolute_db_path(self) -> str:
        """Return the SQLite file path from database_url."""
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url[len("sqlite:///"):]
            p = Path(raw)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            p.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{p}"
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    return Settings()
