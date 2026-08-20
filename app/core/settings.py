from enum import Enum
from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    HttpUrl,
    PostgresDsn,
    RedisDsn,
    SecretStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. __file__ is:       Eveto/app/core/settings.py
# 2. .parent is:        Eveto/app/core/
# 3. .parent.parent is: Eveto/app/
# 4. .parent.parent.parent is: Eveto/  <-- Project Root!
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Environment(str, Enum):
    dev = "dev"
    staging = "staging"
    prod = "prod"


# --- Nested Configurations ---
class DatabaseSettings(BaseModel):
    host: str
    port: int = 5432
    user: str
    password: SecretStr  # Secret: No default
    name: str
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0)

    @property
    def async_dsn(self) -> str:
        """Async DSN for SQLAlchemy 2.0 + asyncpg"""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.user,
                password=self.password.get_secret_value(),
                host=self.host,
                port=self.port,
                path=self.name,
            )
        )


class RedisSettings(BaseModel):
    url: RedisDsn
    cache_ttl: int = 3600

    @property
    def broker_url(self) -> str:
        """Dramatiq broker URL"""
        return str(self.url)


class JWTSettings(BaseModel):
    algorithm: str = "RS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    private_key_path: FilePath  # Validates file exists at startup!
    public_key_path: FilePath

    @property
    def private_key(self) -> str:
        return self.private_key_path.read_text()

    @property
    def public_key(self) -> str:
        return self.public_key_path.read_text()


class MockPaymentSettings(BaseModel):
    base_url: HttpUrl
    api_key: SecretStr  # Secret: No default


class OTelSettings(BaseModel):
    endpoint: str
    service_name: str = "eventhub-api"


# Main Settings
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        env_file=str(BASE_DIR / ".env"),  # Explicitly point to eveto/.env
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    name: str = "eveto-api"
    env: Environment = Environment.dev
    log_level: str = "info"

    # Nested Groups
    db: DatabaseSettings
    redis: RedisSettings
    jwt: JWTSettings
    mock_payment: MockPaymentSettings
    otel: OTelSettings


# Instantiate globally
settings = Settings()
