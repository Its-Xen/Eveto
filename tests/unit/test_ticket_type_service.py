# tests/unit/test_ticket_type_service.py
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.models.event import Event, StatusEnum
from app.models.ticket_type import TicketType
from app.schemas.ticket_type import TicketTypeCreate
from app.services import ticket_type as ticket_type_service  # Import the module


@pytest.fixture
def fake_event():
    return Event(
        id=1,
        venue_id=1,
        title="Coldplay",
        description="Concert",
        starts_at=datetime.now(),
        ends_at=datetime.now() + timedelta(hours=2),
        status=StatusEnum.published,
        created_by_id=1,
        created_at=datetime.now(),
    )


@pytest.fixture
def ticket_in():
    return TicketTypeCreate(
        event_id=1,
        name="VIP",
        price_cents=50000,
        currency="USD",
        total_quantity=100,
        sales_start_at=datetime.now(),
        sales_end_at=datetime.now() + timedelta(days=1),
    )


@patch("app.services.ticket_type.get_event_by_id")
@patch("app.services.ticket_type.create_ticket_type")
@pytest.mark.unit
async def test_create_new_ticket_type_success(
    mock_create_ticket, mock_get_event, fake_event, ticket_in
):
    """Test that a ticket is created when the event exists."""
    db = AsyncMock()
    mock_get_event.return_value = fake_event

    fake_ticket = TicketType(
        id=1, **ticket_in.model_dump(), reserved_quantity=0, sold_quantity=0
    )
    mock_create_ticket.return_value = fake_ticket

    result = await ticket_type_service.create_new_ticket_type(db, ticket_in)

    assert result.id == 1
    assert result.name == "VIP"
    mock_get_event.assert_called_once_with(db, 1)
    mock_create_ticket.assert_called_once()


@patch("app.services.ticket_type.get_event_by_id")
@patch("app.services.ticket_type.create_ticket_type")
@pytest.mark.unit
async def test_create_new_ticket_type_event_not_found(
    mock_create_ticket, mock_get_event, ticket_in
):
    """Test that a NotFoundError is raised if the event doesn't exist."""
    db = AsyncMock()
    mock_get_event.return_value = None

    with pytest.raises(NotFoundError, match="Event with id 1 not found"):
        await ticket_type_service.create_new_ticket_type(db, ticket_in)

    mock_create_ticket.assert_not_called()
