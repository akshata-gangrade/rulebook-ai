from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env.
    """

    # Groq LLM configuration
    groq_api_key: str = Field(
        default="",
        validation_alias="GROQ_API_KEY",
    )

    llm_model: str = Field(
        default="openai/gpt-oss-20b",
        validation_alias="LLM_MODEL",
    )

    # ChromaDB configuration
    chroma_persist_directory: str = Field(
        default="../vector_store/chroma",
        validation_alias="CHROMA_PERSIST_DIRECTORY",
    )

    # Retrieval configuration
    top_k: int = Field(
        default=8,
        validation_alias="TOP_K",
        ge=1,
    )

    similarity_threshold: float = Field(
        default=0.70,
        validation_alias="SIMILARITY_THRESHOLD",
        ge=0.0,
        le=1.0,
    )

    conflict_threshold: float = Field(
        default=0.75,
        validation_alias="CONFLICT_THRESHOLD",
        ge=0.0,
        le=1.0,
    )

    max_context_chunks: int = Field(
        default=6,
        validation_alias="MAX_CONTEXT_CHUNKS",
        ge=1,
    )

    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )

    cors_origins: str = Field(
        default="http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """
        Convert comma-separated CORS origins into a list.
        """
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached application settings instance.
    """
    return Settings()