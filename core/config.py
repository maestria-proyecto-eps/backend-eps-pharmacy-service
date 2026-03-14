from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Variables de Base de Datos
    DB_OP_USER: str
    DB_OP_PASSWORD: str
    DB_OP_HOST: str
    DB_OP_PORT: int = 5432
    DB_OP_NAME: str

    # Variables de JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRES_MINUTES: int

    # Configuración para leer el archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
