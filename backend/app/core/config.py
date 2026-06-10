
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

    # Ollama settings
    OLLAMA_URL: str = Field(default="https://ollama.labb.site", env="OLLAMA_URL")
    OLLAMA_MODEL: str = Field(default="phi3:14b", env="OLLAMA_MODEL")  # Model for translation tasks
    OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text", env="OLLAMA_EMBEDDING_MODEL") # Model for embeddings

    # Redis/Dragonfly settings (for Arq queue)
    REDIS_URL: str = Field(default="redis://dragonfly.dragonfly.svc.cluster.local:6379", env="REDIS_URL")

    # Browserless settings (separated Playwright container)
    BROWSERLESS_URL: str = Field(default="http://browserless:3000", env="BROWSERLESS_URL")

    # Enrichment settings
    ENRICHMENT_LLM_MODEL: str = Field(default="phi3:14b", env="ENRICHMENT_LLM_MODEL")
    ENRICHMENT_BATCH_SIZE: int = Field(default=50, env="ENRICHMENT_BATCH_SIZE")

    model_config = {"env_file": ".env"}

settings = Settings()
