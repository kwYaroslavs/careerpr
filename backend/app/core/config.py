"""Application configuration via pydantic-settings.

Enforces LLM provider selection and privacy consent per docs/LLM_CONTRACTS.md and T-026.
"""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="fake", description="fake, gemini, or ollama")
    llm_privacy_consent: bool = Field(
        default=False,
        description="Must be true to use external LLM providers",
    )

    gemini_api_key: str = Field(default="", description="Gemini API Key")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model name")

    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="llama3", description="Ollama model name")

    database_url: str = Field(default="sqlite:///./data/careerpr.db", description="Database URL")

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in ("fake", "gemini", "ollama"):
            raise ValueError(f"Invalid llm_provider: {v}. Must be 'fake', 'gemini', or 'ollama'.")
        return v_lower

    @field_validator("llm_privacy_consent")
    @classmethod
    def validate_privacy(cls, v: bool, info: Any = None) -> bool:
        return v


def get_settings() -> Settings:
    return Settings()
