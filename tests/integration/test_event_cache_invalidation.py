from datetime import datetime, timedelta

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import get_redis_client
from app.core.security import hash_password
from app.core.settings import settings
from app.db.session import get_db
from app.main import create_app
from app.models.event import Event, StatusEnum
from app.models.user import User, UserRole
from app.models.venue import Venue


@pytest.mark.integration
async def test_event_cache_invalidation(db_engine):
    """Prove that updating an event invalidates the cache"""

    TestSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # * Setup: Create a venue, event, and admin user
    async with TestSessionLocal() as session:
        user = User(
            email="cache@admin.com",
            hashed_password=hash_password("fakehash"),
            full_name="admin",
            role=UserRole.admin,
        )
        session.add(user)
        await session.flush()

        venue = Venue(
            name="Arena",
            address="123 St",
            city="City",
            capacity=1000,
            created_by_id=user.id,
        )
        session.add(venue)
        await session.flush()

        future = datetime.now() + timedelta(days=365)
        event = Event(
            title="Old Title",
            description="Desc",
            starts_at=future,
            ends_at=future + timedelta(hours=3),
            status=StatusEnum.published,
            venue_id=venue.id,
            created_by_id=user.id,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        event_id = event.id

    # * Override dependencies
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    # * Connect to Redis and flush
    redis_url = (
        str(settings.redis.url)
        .replace("redis://redis", "redis://127.0.0.1")
        .replace("localhost", "127.0.0.1")
    )
    redis = aioredis.from_url(redis_url, decode_responses=True)
    await redis.flushdb()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # * Initial Read (Populates the Cache with "Old Title")
        res1 = await client.get("/api/v1/events")
        assert res1.status_code == 200
        assert "Old Title" in res1.text

        # * Login as the admin
        login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": "cache@admin.com", "password": "fakehash"},
        )
        token = login_res.json()["access_token"]

        # * Update the event title (This must trigger cache invalidation!)
        patch_res = await client.patch(
            f"/api/v1/admin/events/{event_id}",
            json={"title": "New Title"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "New Title"

        # * Read again (Should reflect the change, proving cache was invalidated)
        res2 = await client.get("/api/v1/events")
        assert res2.status_code == 200
        assert "New Title" in res2.text
        assert "Old Title" not in res2.text  #! The stale cache was NOT returned!

    # * Cleanup
    await redis.flushdb()
    await redis.close()

    async with TestSessionLocal() as session:
        from sqlalchemy import delete

        await session.execute(delete(Event).where(Event.id == event_id))
        await session.execute(delete(Venue).where(Venue.id == venue.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()
