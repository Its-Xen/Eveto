import pytest

from app.models.ticket_type import TicketType


@pytest.mark.unit
def test_available_quantity_calculation():
    """Test the core bussiness logic for ticket availability."""
    # Create a fake ticket type
    ticket = TicketType(
        id=1,
        event_id=1,
        name="VIP",
        price_cents=5000,
        currency="USD",
        total_quantity=100,
        reserved_quantity=0,
        sold_quantity=0,
    )

    assert ticket.available_quantity == 100

    ticket.reserved_quantity = 5
    assert ticket.available_quantity == 95

    ticket.sold_quantity = 10
    assert ticket.available_quantity == 85


@pytest.mark.unit
def test_availabe_quantity_sold_out():
    """Test that availabilty hits zero correctly."""
    ticket = TicketType(
        id=2,
        event_id=1,
        name="GA",
        price_cents=2000,
        currency="USD",
        total_quantity=50,
        reserved_quantity=50,
        sold_quantity=0,
    )
    assert ticket.available_quantity == 0
