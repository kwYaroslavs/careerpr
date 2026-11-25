"""Application configuration via pydantic-settings.

Enforces LLM provider selection and privacy consent per docs/LLM_CONTRACTS.md and T-026.
"""

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_BACKEND = Path(__file__).resolve().parents[2]
_ROOT = _BACKEND.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT / ".env"), str(_BACKEND / ".env")),  # backend/.env wins
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="fake", description="fake, gemini, deepseek, or ollama")
    llm_privacy_consent: bool = Field(
        default=False,
        description="Must be true to use external LLM providers",
    )

    gemini_api_key: str = Field(default="", description="Gemini API Key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")

    gemini_fallback_models: str = Field(
        default="gemini-2.5-flash-lite,gemini-2.0-flash",
        description="Comma-separated models tried when the main one is overloaded (5xx)",
    )
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    deepseek_model: str = Field(default="deepseek-chat", description="DeepSeek model name")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", description="DeepSeek URL")

    openrouter_api_key: str = Field(default="", description="OpenRouter key(s), comma-separated")
    openrouter_model: str = Field(default="", description="Free model id; empty = auto")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")

    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="llama3", description="Ollama model name")

    database_url: str = Field(default="sqlite:///./data/careerpr.db", description="Database URL")
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> Any:
        """Accept a JSON list or a comma-separated string."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in ("fake", "gemini", "deepseek", "openrouter", "ollama"):
            raise ValueError(
                f"Invalid llm_provider: {v}. Must be fake/gemini/deepseek/openrouter/ollama."
            )
        return v_lower

    @field_validator("llm_privacy_consent")
    @classmethod
    def validate_privacy(cls, v: bool, info: Any = None) -> bool:
        return v


def get_settings() -> Settings:
    return Settings()
