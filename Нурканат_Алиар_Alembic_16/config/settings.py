from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import  RedisDsn, Field, AnyUrl

class Settings(BaseSettings):
    APP_NAME: str = "FastAPI app"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., min_length=1)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    REDIS_URL: RedisDsn = Field("redis://redis:6379/0")
    REDIS_POOL_SIZE: int = 5

    CORS_ORIGINS: str = "*"
    CORS_METHODS: str = "*"
    CORS_HEADERS: str = "*"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()