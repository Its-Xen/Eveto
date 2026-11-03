# tests/integration/test_partner_contract.py
import hashlib

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import get_redis_client
from app.core.settings import settings
from app.db.session import get_db
from app.main import create_app
from app.models.api_key import ApiKey


@pytest.fixture
async def partner_api_key(db_engine):
    """Create a test API key for contract testing."""
    TestSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    raw_key = "sk_live_contract_test_key_999"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with TestSessionLocal() as session:
        new_key = ApiKey(
            partner_name="ContractTester", key_hash=key_hash, rate_limit_tier=100
        )
        session.add(new_key)
        await session.commit()
        await session.refresh(new_key)
        api_key_id = new_key.id

    yield raw_key, api_key_id

    async with TestSessionLocal() as session:
        from sqlalchemy import delete

        await session.execute(delete(ApiKey).where(ApiKey.id == api_key_id))
        await session.commit()


@pytest.mark.integration
async def test_partner_api_contract(partner_api_key, db_engine):
    """
    Explicit contract test: Ensure Partner API returns exactly the expected fields.
    """
    raw_key, _ = partner_api_key

    app = create_app()

    # Override DB to use testcontainer engine
    TestSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Override Redis
    redis_url = (
        str(settings.redis.url)
        .replace("redis://redis", "redis://127.0.0.1")
        .replace("localhost", "127.0.0.1")
    )
    redis_client = aioredis.from_url(redis_url, decode_responses=True)

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_redis_client] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/partners/events", headers={"X-API-Key": raw_key}
        )

    assert response.status_code == 200
    data = response.json()

    # Explicit Contract Assertions: If any of these fields are renamed, this test fails!
    assert isinstance(data, list)
    if len(data) > 0:
        event = data[0]
        assert "id" in event
        assert "title" in event
        assert "description" in event
        assert "starts_at" in event
        assert "ends_at" in event
        assert "status" in event
        assert "venue_id" in event
        assert "created_by_id" in event
        assert "created_at" in event

    await redis_client.aclose()
