import asyncio
from datetime import datetime, timedelta

from app.core.security import hash_password

# Assuming i have a hashing function, or a dummy string
from app.db.session import AsyncSessionLocal
from app.models.event import Event, StatusEnum
from app.models.ticket_type import TicketType
from app.models.user import User, UserRole
from app.models.venue import Venue


async def seed_db() -> None:
    print("Starting database seeding...")

    # * open db session
    async with AsyncSessionLocal() as db:
        # Create a fake admin User
        admin = User(
            email="admin@eveto.com",
            hashed_password=hash_password("fakehashesdpass123"),
            full_name="Admin User",
            role=UserRole.admin,
        )
        db.add(admin)
        await db.flush()  # get the admin's id without committing yet

        # Create a fake Venue
        venue = Venue(
            name="Madison square garden",
            address="4 Pennsylvania Plaza",
            city="New York",
            capacity=20000,
            created_by_id=admin.id,
        )
        db.add(venue)
        await db.flush()

        # Create a fake Event
        event = Event(
            title="Coldplay Live",
            description="A Music of the Spheres concert",
            starts_at=datetime.now() + timedelta(days=30),
            ends_at=datetime.now() + timedelta(days=30, hours=3),
            status=StatusEnum.published,
            venue_id=venue.id,
            created_by_id=admin.id,
            created_at=datetime.now(),
        )
        db.add(event)
        await db.flush()

        # Create fake ticket types
        vip_ticket = TicketType(
            name="VIP Pass",
            price_cents=50000,  # $500.00
            currency="USD",
            total_quantity=100,
            reserved_quantity=0,
            sold_quantity=0,
            sales_start_at=datetime.now(),
            sales_end_at=datetime.now() + timedelta(days=29),
            event_id=event.id,
        )
        general_ticket = TicketType(
            name="General Admission",
            price_cents=10000,  # $100.00
            currency="USD",
            total_quantity=5000,
            reserved_quantity=0,
            sold_quantity=0,
            sales_start_at=datetime.now(),
            sales_end_at=datetime.now() + timedelta(days=29),
            event_id=event.id,
        )

        db.add_all([vip_ticket, general_ticket])

        # * Commit to save everything to db(for mine is postgres)
        await db.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_db())
