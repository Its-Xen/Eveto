import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_db
from app.main import create_app


@pytest.mark.integration
async def test_register_login_and_access_protected_route(db_engine):
    """End-to-end test of the auth flow against a real DB."""

    # * Create a test db session factory
    TestSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # * Override FastAPI's get_db dependency to use our test session
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # * Create the HTTP client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "e2e@test.com",
                "password": "testpassword123",
                "full_name": "E2E Tester",
            },
        )
        assert register_response.status_code == 201

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "e2e@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # ACCESS PROTECTED ROUTE (/me)
        me_response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "e2e@test.com"

    # Clean up the user we just created
    async with TestSessionLocal() as session:
        from sqlalchemy import delete

        from app.models.user import User

        await session.execute(delete(User).where(User.email == "e2e@test.com"))
        await session.commit()
