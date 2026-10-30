
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
    INTERNAL_AUTH_TOKEN: str = Field(default="internal-secret-token", env="INTERNAL_AUTH_TOKEN")  # Empty = skip header check, IP check alone applies

    # Authentik ForwardAuth settings
    INTERNAL_NETWORKS: list[str] = Field(default=["127.0.0.1/32", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"], env="INTERNAL_NETWORKS")
    AUTHENTIK_ADMIN_GROUP: str = Field(default="stipendariet-admins", env="AUTHENTIK_ADMIN_GROUP")

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

    # SearXNG self-hosted search
    SEARXNG_URL: str = Field(default="http://searxng:8080", env="SEARXNG_URL")
    SEARXNG_RATE_LIMIT: float = Field(default=1.0, env="SEARXNG_RATE_LIMIT")
    SEARXNG_TIMEOUT: float = Field(default=10.0, env="SEARXNG_TIMEOUT")
    SEARXNG_MAX_RETRIES: int = Field(default=3, env="SEARXNG_MAX_RETRIES")
    SEARXNG_ENGINES: list[str] = Field(default=["google", "bing", "duckduckgo", "brave"], env="SEARXNG_ENGINES")

    # Bolagsverket API settings (for Enrichment Pipeline v2 Stage 0)
    BOLAGSVERKET_URL: str = Field(
        default="https://data.bolagsverket.se/api",
        env="BOLAGSVERKET_URL"
    )
    BOLAGSVERKET_API_KEY: str = Field(
        default="",
        env="BOLAGSVERKET_API_KEY"
    )  # Optional OAuth 2.0 Bearer token for production use
    BOLAGSVERKET_RATE_LIMIT: float = Field(
        default=1.0,
        env="BOLAGSVERKET_RATE_LIMIT"
    )  # Requests per second (Bolagsverket ToS: 60/min = 1/sec)
    BOLAGSVERKET_MAX_RETRIES: int = Field(
        default=3,
        env="BOLAGSVERKET_MAX_RETRIES"
    )  # Number of retry attempts with exponential backoff
    BOLAGSVERKET_TIMEOUT: float = Field(
        default=10.0,
        env="BOLAGSVERKET_TIMEOUT"
    )  # HTTP request timeout in seconds

    # Enrichment settings
    ENRICHMENT_LLM_MODEL: str = Field(default="gemma-4-12b", env="ENRICHMENT_LLM_MODEL")
    ENRICHMENT_BATCH_SIZE: int = Field(default=50, env="ENRICHMENT_BATCH_SIZE")

    # Batch processing settings
    EMBEDDING_BATCH_SIZE: int = Field(default=100, env="EMBEDDING_BATCH_SIZE")
    TRANSLATION_CONCURRENCY: int = Field(default=3, env="TRANSLATION_CONCURRENCY")
    TRANSLATION_DELAY: float = Field(default=0.1, env="TRANSLATION_DELAY")

    # Crawler settings (Phase 3 - Trafilatura-first)
    CRAWL_POLITE_DELAY: float = Field(default=1.0, env="CRAWL_POLITE_DELAY")
    CRAWL_MIN_CONTENT_LENGTH: int = Field(default=500, env="CRAWL_MIN_CONTENT_LENGTH")
    CRAWL_MAX_SUBPAGES: int = Field(default=5, env="CRAWL_MAX_SUBPAGES")
    CRAWL_TIMEOUT: int = Field(default=30, env="CRAWL_TIMEOUT")
    CRAWLER_USER_AGENT: str = Field(
        default="StipendarietBot/1.0 (+https://stipendariet.se)",
        env="CRAWLER_USER_AGENT"
    )

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
