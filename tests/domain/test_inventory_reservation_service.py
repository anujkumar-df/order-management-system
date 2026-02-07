"""Unit tests for the InventoryReservationService domain service."""

import pytest

from oms.domain.exceptions import EntityNotFoundError, ValidationError
from oms.domain.model.inventory import InventoryItem
from oms.domain.model.order import Order, OrderLineItem
from oms.domain.model.value_objects import Money, Quantity
from oms.domain.service.inventory_reservation_service import (
    InventoryReservationService,
)
from tests.fakes import FakeInventoryRepository


def _make_order(items: list[tuple[str, str, int]]) -> Order:
    """Create an order with given (product_id, product_name, qty) tuples."""
    line_items = [
        OrderLineItem(
            product_id=pid,
            product_name=pname,
            quantity=Quantity(qty),
            unit_price=Money.of("10.00"),
        )
        for pid, pname, qty in items
    ]
    order = Order(id=1, customer_name="Test", items=line_items)
    return order


def _make_inventory(*specs: tuple[str, str, int, int]) -> FakeInventoryRepository:
    """Create repo with (product_id, name, total, reserved) tuples."""
    items = [
        InventoryItem(product_id=pid, product_name=name, total_quantity=total, reserved_quantity=reserved)
        for pid, name, total, reserved in specs
    ]
    return FakeInventoryRepository(items)


class TestReserveForOrder:

    def test_reserves_all_items(self):
        repo = _make_inventory(("1", "Widget", 100, 0), ("2", "Gadget", 50, 0))
        order = _make_order([("1", "Widget", 10), ("2", "Gadget", 5)])
        svc = InventoryReservationService(repo)

        svc.reserve_for_order(order)

        assert repo.get_by_product_id("1").reserved_quantity == 10
        assert repo.get_by_product_id("1").available_quantity == 90
        assert repo.get_by_product_id("2").reserved_quantity == 5
        assert repo.get_by_product_id("2").available_quantity == 45

    def test_insufficient_stock_rejected(self):
        repo = _make_inventory(("1", "Widget", 5, 0))
        order = _make_order([("1", "Widget", 10)])
        svc = InventoryReservationService(repo)

        with pytest.raises(ValidationError, match="Insufficient inventory for Widget"):
            svc.reserve_for_order(order)

    def test_no_partial_reservation_on_failure(self):
        """If Widget succeeds but Gadget fails, Widget should NOT be reserved."""
        repo = _make_inventory(("1", "Widget", 100, 0), ("2", "Gadget", 3, 0))
        order = _make_order([("1", "Widget", 10), ("2", "Gadget", 5)])
        svc = InventoryReservationService(repo)

        with pytest.raises(ValidationError, match="Insufficient inventory for Gadget"):
            svc.reserve_for_order(order)

        # Widget should NOT have been reserved (two-phase approach)
        assert repo.get_by_product_id("1").reserved_quantity == 0
        assert repo.get_by_product_id("2").reserved_quantity == 0

    def test_missing_inventory_record_rejected(self):
        repo = _make_inventory()  # empty
        order = _make_order([("1", "Widget", 10)])
        svc = InventoryReservationService(repo)

        with pytest.raises(EntityNotFoundError, match="No inventory record"):
            svc.reserve_for_order(order)

    def test_reserves_with_existing_reservations(self):
        repo = _make_inventory(("1", "Widget", 100, 50))
        order = _make_order([("1", "Widget", 30)])
        svc = InventoryReservationService(repo)

        svc.reserve_for_order(order)

        assert repo.get_by_product_id("1").reserved_quantity == 80
        assert repo.get_by_product_id("1").available_quantity == 20


class TestReleaseForOrder:

    def test_releases_all_items(self):
        repo = _make_inventory(("1", "Widget", 100, 10), ("2", "Gadget", 50, 5))
        order = _make_order([("1", "Widget", 10), ("2", "Gadget", 5)])
        svc = InventoryReservationService(repo)

        svc.release_for_order(order)

        assert repo.get_by_product_id("1").reserved_quantity == 0
        assert repo.get_by_product_id("1").available_quantity == 100
        assert repo.get_by_product_id("2").reserved_quantity == 0
        assert repo.get_by_product_id("2").available_quantity == 50

    def test_partial_release(self):
        repo = _make_inventory(("1", "Widget", 100, 30))
        order = _make_order([("1", "Widget", 10)])
        svc = InventoryReservationService(repo)

        svc.release_for_order(order)

        assert repo.get_by_product_id("1").reserved_quantity == 20
