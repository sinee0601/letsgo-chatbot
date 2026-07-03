from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    mongo_url: str
    mongo_db: str
    redis_url: str
    keyword_cache_ttl: int = 60 * 60 * 24
    gemini_model: str
    system_instruction: str | None = None
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    cache_similarity_threshold: float = 0.92

    class Config:
        env_file = ".env"


settings = Settings()
