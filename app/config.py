from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    gemini_model: str
    system_instruction: str | None = None

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
