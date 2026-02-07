"""Unit tests for fulfillment-related domain logic."""

import pytest

from oms.domain.exceptions import ValidationError
from oms.domain.model.inventory import InventoryItem
from oms.domain.model.order import Order, OrderLineItem, OrderStatus
from oms.domain.model.value_objects import Money, Quantity
from oms.domain.service.inventory_reservation_service import (
    InventoryReservationService,
)
from tests.fakes import FakeInventoryRepository


# ── Order.fulfill() state transition ─────────────────────────────────────────


class TestOrderFulfill:

    def _make_confirmed_order(self) -> Order:
        order = Order(
            id=1,
            customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(5), Money.of("10.00")),
            ],
            status=OrderStatus.CONFIRMED,
        )
        return order

    def test_confirm_to_fulfilled(self):
        order = self._make_confirmed_order()
        order.fulfill()
        assert order.status == OrderStatus.FULFILLED

    def test_fulfill_draft_rejected(self):
        order = Order(
            id=1, customer_name="Bob",
            items=[OrderLineItem("1", "Widget", Quantity(1), Money.of("10.00"))],
            status=OrderStatus.DRAFT,
        )
        with pytest.raises(ValidationError, match="Cannot fulfill order in DRAFT status"):
            order.fulfill()

    def test_fulfill_cancelled_rejected(self):
        order = Order(
            id=1, customer_name="Bob",
            items=[OrderLineItem("1", "Widget", Quantity(1), Money.of("10.00"))],
            status=OrderStatus.CANCELLED,
        )
        with pytest.raises(ValidationError, match="Cannot fulfill order in CANCELLED status"):
            order.fulfill()

    def test_fulfill_already_fulfilled_rejected(self):
        order = self._make_confirmed_order()
        order.fulfill()
        with pytest.raises(ValidationError, match="Order already fulfilled"):
            order.fulfill()


class TestCancelFulfilledOrder:

    def test_cancel_fulfilled_rejected(self):
        order = Order(
            id=1, customer_name="Bob",
            items=[OrderLineItem("1", "Widget", Quantity(1), Money.of("10.00"))],
            status=OrderStatus.FULFILLED,
        )
        with pytest.raises(ValidationError, match="Cannot cancel order in FULFILLED status"):
            order.cancel()


# ── InventoryItem.fulfill() ──────────────────────────────────────────────────


class TestInventoryItemFulfill:

    def test_fulfill_deducts_total_and_reserved(self):
        inv = InventoryItem("1", "Widget", total_quantity=100, reserved_quantity=20)
        inv.fulfill(20)
        assert inv.total_quantity == 80
        assert inv.reserved_quantity == 0
        assert inv.available_quantity == 80

    def test_partial_fulfill(self):
        inv = InventoryItem("1", "Widget", total_quantity=100, reserved_quantity=30)
        inv.fulfill(10)
        assert inv.total_quantity == 90
        assert inv.reserved_quantity == 20
        assert inv.available_quantity == 70

    def test_fulfill_more_than_reserved_rejected(self):
        inv = InventoryItem("1", "Widget", total_quantity=100, reserved_quantity=5)
        with pytest.raises(ValidationError, match="Cannot fulfill"):
            inv.fulfill(10)

    def test_fulfill_zero_rejected(self):
        inv = InventoryItem("1", "Widget", total_quantity=100, reserved_quantity=10)
        with pytest.raises(ValidationError, match="must be positive"):
            inv.fulfill(0)


# ── InventoryReservationService.fulfill_for_order() ──────────────────────────


class TestFulfillForOrder:

    def test_fulfill_deducts_all_items(self):
        repo = FakeInventoryRepository([
            InventoryItem("1", "Widget", total_quantity=100, reserved_quantity=20),
            InventoryItem("2", "Gadget", total_quantity=50, reserved_quantity=10),
        ])
        order = Order(
            id=1, customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(20), Money.of("10.00")),
                OrderLineItem("2", "Gadget", Quantity(10), Money.of("10.00")),
            ],
            status=OrderStatus.FULFILLED,
        )

        svc = InventoryReservationService(repo)
        svc.fulfill_for_order(order)

        w = repo.get_by_product_id("1")
        assert w.total_quantity == 80
        assert w.reserved_quantity == 0
        assert w.available_quantity == 80

        g = repo.get_by_product_id("2")
        assert g.total_quantity == 40
        assert g.reserved_quantity == 0
        assert g.available_quantity == 40
