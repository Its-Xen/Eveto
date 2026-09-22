import pytest

from app.models.user import User, UserRole
from app.repositories.venue import create_venue, get_venue_by_id


@pytest.mark.integration
async def test_create_and_get_venue(db_session):
    """Test that we can create a venue and fetch it back from the real DB."""

    # We need a user to satisfy the created_by_id foreign key
    fake_user = User(
        email="integration@test.com",
        hashed_password="fakehash",
        full_name="Test User",
        role=UserRole.admin,
    )
    db_session.add(fake_user)
    await db_session.commit()
    await db_session.refresh(fake_user)

    # Create a venue using the repository
    venue_data = {
        "name": "Integration Arena",
        "address": "123 Test St",
        "city": "Testville",
        "capacity": 5000,
    }
    new_venue = await create_venue(db_session, venue_data, user_id=fake_user.id)

    # Verify it was assigned an ID
    assert new_venue.id is not None

    # Fetch it using the repository
    fetched_venue = await get_venue_by_id(db_session, new_venue.id)

    assert fetched_venue is not None
    assert fetched_venue.name == "Integration Arena"
    assert fetched_venue.capacity == 5000
