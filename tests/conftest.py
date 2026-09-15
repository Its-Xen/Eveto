import pytest

from app.core.settings import Environment, Settings

pytest.fixture(scope="session")


def test_settings() -> Settings:
    """Override Pydantic Settings for the test environment."""
    return Settings(
        env=Environment.dev,
        log_level="info",
        cors_origins=["*"],
        db={
            "host": "localhost",
            "port": 5432,
            "user": "test_user",
            "password": "test_password",
            "name": "test_db",
            "pool_size": 5,
            "max_overflow": 5,
        },
        redis={
            "url": "redis://localhost:6379/0",
            "cache_ttl": 100,
        },
        jwt={
            "algorithm": "RS256",
            "access_token_expire_minutes": 15,
            "private_key_path": "tests/fake_keys/private.pem",
            "public_key_path": "tests/fake_keys/public.pem",
        },
        mock_payment={
            "base_url": "http://mock-payment:8000",
            "api_key": "test_payment_key",
        },
        otel={
            "endpoint": "http://otel:4317",
            "service_name": "eventhub-test",
        },
    )
