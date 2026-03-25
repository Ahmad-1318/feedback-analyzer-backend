from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str
    DATABASE_NAME: str = "feedback_app"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GROQ_API_KEY: str
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw_origins = [o.strip() for o in self.FRONTEND_URL.split(",") if o.strip()]
        origins = [o.rstrip("/") for o in raw_origins]
        
        if "http://localhost:3000" not in origins:
            origins.append("http://localhost:3000")
        if "http://127.0.0.1:3000" not in origins:
            origins.append("http://127.0.0.1:3000")
        return origins

    class Config:
        env_file = ".env"
        extra = "ignore"


try:
    settings = Settings()
    import logging
    logging.info(f"ALLOWED CORS ORIGINS: {settings.CORS_ORIGINS}")
except Exception as e:
    import logging
    logging.error(f"FATAL: Missing or invalid environment variables: {e}")
    raise
