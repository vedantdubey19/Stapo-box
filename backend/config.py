"""Application configuration and environment settings.

Loads environment variables from .env and provides strongly typed
configuration values for LLM, search, vector database, and API server.
"""

from typing import List, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    # ── LLM Configuration ──────────────────────────────────────────
    LLM_PROVIDER: Literal["gemini", "openai", "claude"] = Field(
        default="gemini",
        description="Active LLM provider backend",
    )
    GEMINI_API_KEY: str = Field(
        default="",
        description="Primary Google Gemini API key (supports comma-separated list of keys)",
    )
    GEMINI_API_KEY_2: str = Field(
        default="",
        description="Secondary Google Gemini API key for dual-API load balancing and enhanced speed",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-flash-lite-latest",
        description="Gemini model identifier (e.g. gemini-flash-lite-latest, gemini-2.5-flash)",
    )
    LLM_MAX_RPM: int = Field(
        default=30,
        description="Maximum requests per minute per key (client-side rate limiter)",
    )
    GEMINI_MAX_RPM: int = Field(
        default=30,
        description="Alias for Gemini RPM ceiling",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key (optional)",
    )
    CLAUDE_API_KEY: str = Field(
        default="",
        description="Anthropic Claude API key (optional)",
    )

    # ── Retrieval Layer ─────────────────────────────────────────────
    TAVILY_API_KEY: str = Field(
        default="",
        description="Tavily Web Search API key",
    )
    CHROMA_PERSIST_DIR: str = Field(
        default="./data/chroma_db",
        description="Filesystem directory for ChromaDB vector store",
    )

    # ── Server & Runtime Config ─────────────────────────────────────
    BACKEND_HOST: str = Field(
        default="127.0.0.1",
        description="Host address for FastAPI server",
    )
    BACKEND_PORT: int = Field(
        default=8000,
        description="Port for FastAPI server",
    )
    API_TIMEOUT_SECONDS: int = Field(
        default=15,
        description="Timeout in seconds for external API calls",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Application logging level",
    )

    # ── Domain Constants (Locked Spec) ──────────────────────────────
    ALLOWED_SPORTS: List[str] = Field(
        default_factory=lambda: [
            "Cricket",
            "Football",
            "Tennis",
            "Badminton",
            "Basketball",
        ]
    )
    ALLOWED_DIFFICULTIES: List[str] = Field(
        default_factory=lambda: ["Easy", "Medium", "Hard"]
    )
    ALLOWED_CONTENT_TYPES: List[str] = Field(
        default_factory=lambda: [
            "MCQ",
            "True/False",
            "This-or-That",
            "Fill in the Blank",
            "Guess the Number",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()
