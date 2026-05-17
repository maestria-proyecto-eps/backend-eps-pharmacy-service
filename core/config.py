from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_OP_USER: str
    DB_OP_PASSWORD: str
    DB_OP_HOST: str
    DB_OP_PORT: int = 5432
    DB_OP_NAME: str

    DB_ADMIN_USER: str
    DB_ADMIN_PASSWORD: str
    DB_ADMIN_HOST: str
    DB_ADMIN_PORT: int = 5432
    DB_ADMIN_NAME: str

    JWT_EXPIRES_MINUTES: int
    JWT_SECRET: str
    JWT_ALGORITHM: str

    model_config = SettingsConfigDict(
        env_file=(".env"),
        extra="ignore"
    )

settings = Settings()