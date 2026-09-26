import functools

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Every value is sourced from the environment. There are intentionally
    NO fallback/default values for required configuration: if a required
    variable is missing, instantiation raises a validation error and the
    application fails fast at startup with a clear message.

    `.env` is read only as a convenience for local/compose runs; in a cloud
    deployment the same variables are provided by the container environment.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Runtime ---
    ENVIRONMENT: str = Field(..., description="deployment environment, e.g. development|staging|production")
    BACKEND_PORT: int = Field(..., description="port the API server binds to")
    API_BASE_URL: str = Field(..., description="public base URL the API is reached at")
    # Comma-separated string in the environment (parsed via the `cors_origins`
    # property). Kept as `str` so pydantic-settings does not attempt to JSON
    # decode it, which is a known pitfall for list-typed settings.
    CORS_ORIGINS: str = Field(..., description="comma-separated list of allowed browser origins")

    # --- Database (Supabase Postgres) ---
    DATABASE_URL: str = Field(..., description="async SQLAlchemy DSN, e.g. postgresql+asyncpg://...")
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key (secret)")

    # --- AI providers ---
    GROQ_API_KEY: str = Field(..., description="Groq API key (secret)")
    GROQ_MODEL: str = Field(..., description="Groq chat model identifier")
    HUGGINGFACE_API_KEY: str = Field(..., description="HuggingFace API key (secret)")

    # --- Document Upload & OCR ---
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=10 * 1024 * 1024,
        description="maximum allowed file upload size in bytes (default: 10MB)",
    )
    OCR_ENABLED: bool = Field(
        default=True,
        description="whether OCR fallback is enabled for scanned documents",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("ENVIRONMENT")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        allowed = {"production", "staging", "test"}
        if value not in allowed:
            raise ValueError(
                f"ENVIRONMENT must be one of {sorted(allowed)}, got '{value}'. "
                "Development environments (e.g. 'development', 'dev') are not permitted in production configuration."
            )
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _validate_cors(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("CORS_ORIGINS must be a non-empty comma-separated list of origins")
        return value

    @model_validator(mode="after")
    def _validate_production_cors(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            origins = self.cors_origins
            if any(origin == "*" for origin in origins):
                raise ValueError(
                    "CORS_ORIGINS cannot use wildcard '*' in production environment. "
                    "Specify explicit allowed origins (e.g. 'https://your-production-frontend-domain.com')."
                )
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Raises pydantic ValidationError (fail fast) if any required environment
    variable is missing or invalid.
    """
    return Settings()  # type: ignore[call-arg]
