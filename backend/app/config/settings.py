from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "AEROGRID_"}

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Database — SQLite by default for local dev, PostgreSQL for production
    database_url: str = "sqlite+aiosqlite:///./aerogrid.db"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_prompt_version: str = "v3.2"
    gemini_schema_version: str = "v2.1"
    gemini_timeout_seconds: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Providers
    weather_api_url: str = "https://api.open-meteo.com/v1"
    firms_api_url: str = "https://firms.modaps.eosdis.nasa.gov/api"
    cpcb_api_url: str = ""

    # Rate limiting
    rate_limit_per_ip: int = 100  # requests per minute
    rate_limit_per_device: int = 10  # observations per hour

    # Correlation thresholds (canonical — see S4.6)
    threshold_watch: float = 0.3
    threshold_probable_hotspot: float = 0.5
    threshold_high_confidence: float = 0.7

    # Minimum observations (see S5.1)
    min_observations_watch: int = 1
    min_observations_probable_hotspot: int = 3
    min_observations_high_confidence: int = 5
    min_source_types_probable_hotspot: int = 2
    min_source_types_high_confidence: int = 2

    # Composite scoring weights (see S4.6)
    weight_semantic: float = 0.30
    weight_spatial: float = 0.25
    weight_temporal: float = 0.20
    weight_independence: float = 0.15
    weight_environmental: float = 0.10

    # Expiry (seconds)
    watch_expiry_seconds: int = 1800  # 30 minutes
    probable_hotspot_expiry_seconds: int = 21600  # 6 hours
    high_confidence_expiry_seconds: int = 86400  # 24 hours


settings = Settings()
