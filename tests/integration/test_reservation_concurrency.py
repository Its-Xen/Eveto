import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_db
from app.main import create_app
from app.models.event import Event, StatusEnum
from app.models.ticket_type import TicketType
from app.models.user import User, UserRole
from app.models.venue import Venue


@pytest.mark.integration
async def test_flash_sale_no_overselling(db_engine):
    """Simulate a flash sale with 20 users fighting for 10 tickets."""

    TestSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # * Setup: Create a venue, event, and exactly 10 tickets
    async with TestSessionLocal() as session:
        user = User(
            email="flashsale@admin.com",
            hashed_password="fakehash",
            full_name="Admin",
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

        future_date = datetime.now(timezone.utc) + timedelta(days=365)

        event = Event(
            title="Flash Sale Concert",
            description="Hot",
            starts_at=future_date,
            ends_at=future_date + timedelta(hours=3),
            status=StatusEnum.published,
            venue_id=venue.id,
            created_by_id=user.id,
        )
        session.add(event)
        await session.flush()

        ticket_type = TicketType(
            event_id=event.id,
            name="GA",
            price_cents=5000,
            currency="USD",
            total_quantity=10,
            reserved_quantity=0,
            sold_quantity=0,
            sales_start_at=datetime.now(timezone.utc),
            sales_end_at=future_date,
        )
        session.add(ticket_type)
        await session.commit()
        await session.refresh(ticket_type)

        ticket_type_id = ticket_type.id

    # * Override FastAPI's DB dependency
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # * Fire 20 CONCURRENT reservation requests
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def buy_ticket(buyer_id: int) -> int:
            """Helper to register a user and try to buy a ticket simultaneously."""
            # Register a new user
            await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"buyer{buyer_id}@test.com",
                    "password": "testpassword123",
                    "full_name": f"Buyer {buyer_id}",
                },
            )
            # Login
            login_resp = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"buyer{buyer_id}@test.com",
                    "password": "testpassword123",
                },
            )
            token = login_resp.json()["access_token"]

            # Attempt to reserve 1 ticket
            resp = await client.post(
                "/api/v1/reservations",
                json={"ticket_type_id": ticket_type_id, "quantity": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.status_code

        # Run all 20 requests at the EXACT same millisecond
        tasks = [buy_ticket(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

    # * Assertions
    successful_reservations = results.count(201)
    conflict_errors = results.count(409)

    print(
        f"\n[CONCURRENCY TEST] Successful: {successful_reservations}"
        f"| Conflicts: {conflict_errors}"
    )

    # * Assert exactly 10 succeeded, and exactly 10 were rejected
    assert successful_reservations == 10
    assert conflict_errors == 10

    # * Verify the database math is perfectly accurate
    async with TestSessionLocal() as session:
        db_ticket = (
            await session.execute(
                select(TicketType).where(TicketType.id == ticket_type_id)
            )
        ).scalar_one()
        assert db_ticket.reserved_quantity == 10
        assert db_ticket.available_quantity == 0
        print(
            "[CONCURRENCY TEST] ✅ Database verified: 0 tickets left. No overselling!"
        )
