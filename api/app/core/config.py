"""
config.py — Configuração da aplicação via .env (pydantic-settings).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres
    database_url: str = "postgresql+psycopg://health:health@localhost:5432/health_agents"

    # App
    app_name: str = "Health Agents API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Auth (futuro: OAuth2 / JWT)
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM opcional (OpenRouter — API compatível com OpenAI). Com
    # llm_enabled=False (padrão), o chat continua 100% determinístico e
    # offline, como sempre foi. Ver README para como habilitar.
    llm_enabled: bool = False
    openrouter_api_key: str = ""
    openrouter_model: str = ""  # ex.: "anthropic/claude-haiku-4.5" — ver openrouter.ai/models
    openrouter_base_url: str = "https://openrouter.ai/api/v1"


settings = Settings()
