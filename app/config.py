from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    mongo_url: str
    mongo_db: str
    redis_url: str
    keyword_cache_ttl: int = 60 * 60 * 24
    gemini_model: str
    system_instruction: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
