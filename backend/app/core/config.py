
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    DATABASE_USER: str = Field(default="postgres", env="DATABASE_USER")
    DATABASE_PASSWORD: str = Field(default="postgres", env="DATABASE_PASSWORD")
    DATABASE_HOST: str = Field(default="localhost", env="DATABASE_HOST")
    DATABASE_PORT: str = Field(default="5432", env="DATABASE_PORT")
    DATABASE_NAME: str = Field(default="stipendariet", env="DATABASE_NAME")

    # Admin credentials
    ADMIN_USERNAME: str = Field(default="admin", env="ADMIN_USERNAME")
    ADMIN_PASSWORD: str = Field(default="placeholder-password", env="ADMIN_PASSWORD")
    ADMIN_EMAIL: str = Field(default="davidbaeriksson@gmail.com", env="ADMIN_EMAIL")

    # JWT
    JWT_SECRET_KEY: str = Field(default="change-me", env="JWT_SECRET_KEY")

    # Internal auth (for service-to-service calls)
    INTERNAL_AUTH_TOKEN: str = Field(default="internal-secret-token", env="INTERNAL_AUTH_TOKEN")

    # Foundation sync
    FOUNDATION_BATCH_SIZE: int = Field(default=500, env="FOUNDATION_BATCH_SIZE")

    # LiteLLM settings (OpenAI-compatible proxy for all LLM/embedding calls)
    LITELLM_URL: str = Field(default="http://litellm.litellm.svc.cluster.local:4000", env="LITELLM_URL")
    LITELLM_API_KEY: str = Field(default="", env="LITELLM_API_KEY")  # Optional for internal calls
    LITELLM_TEXT_MODEL: str = Field(default="gemma-4-12b", env="LITELLM_TEXT_MODEL")  # Model for translation/generation tasks
    LITELLM_EMBEDDING_MODEL: str = Field(default="nomic-embed-text-v2", env="LITELLM_EMBEDDING_MODEL")

    # Redis/Dragonfly settings (for Arq queue)
    REDIS_URL: str = Field(default="redis://dragonfly.dragonfly.svc.cluster.local:6379", env="REDIS_URL")

    # Browserless settings (separated Playwright container)
    BROWSERLESS_URL: str = Field(default="http://browserless:3000", env="BROWSERLESS_URL")

    # Enrichment settings
    ENRICHMENT_LLM_MODEL: str = Field(default="gemma-4-12b", env="ENRICHMENT_LLM_MODEL")
    ENRICHMENT_BATCH_SIZE: int = Field(default=50, env="ENRICHMENT_BATCH_SIZE")

    model_config = {"env_file": ".env"}

settings = Settings()
