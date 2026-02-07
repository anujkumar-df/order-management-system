"""Unit tests for partial fulfillment domain logic."""

import pytest

from oms.domain.exceptions import ValidationError
from oms.domain.model.order import Order, OrderLineItem, OrderStatus
from oms.domain.model.value_objects import Money, Quantity


# ── OrderLineItem.ship() ─────────────────────────────────────────────────────


class TestOrderLineItemShip:

    def _make_item(self, qty: int = 10) -> OrderLineItem:
        return OrderLineItem("1", "Widget", Quantity(qty), Money.of("15.00"))

    def test_ship_increments_shipped_quantity(self):
        item = self._make_item(10)
        item.ship(3)
        assert item.shipped_quantity == 3
        assert item.remaining_quantity == 7

    def test_ship_multiple_times(self):
        item = self._make_item(10)
        item.ship(3)
        item.ship(4)
        assert item.shipped_quantity == 7
        assert item.remaining_quantity == 3

    def test_ship_all_remaining(self):
        item = self._make_item(10)
        item.ship(10)
        assert item.shipped_quantity == 10
        assert item.remaining_quantity == 0
        assert item.is_fully_shipped

    def test_ship_zero_rejected(self):
        item = self._make_item(10)
        with pytest.raises(ValidationError, match="must be positive"):
            item.ship(0)

    def test_ship_negative_rejected(self):
        item = self._make_item(10)
        with pytest.raises(ValidationError, match="must be positive"):
            item.ship(-1)

    def test_ship_more_than_remaining_rejected(self):
        item = self._make_item(5)
        item.ship(3)
        with pytest.raises(ValidationError, match="only 2 remaining"):
            item.ship(3)

    def test_line_total_unchanged_after_ship(self):
        item = self._make_item(10)
        total_before = item.line_total
        item.ship(5)
        assert item.line_total == total_before


# ── Order.fulfill_items() — partial fulfillment ──────────────────────────────


class TestOrderFulfillItems:

    def _make_confirmed_order(self) -> Order:
        return Order(
            id=1,
            customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(10), Money.of("15.00")),
                OrderLineItem("2", "Gadget", Quantity(5), Money.of("25.00")),
            ],
            status=OrderStatus.CONFIRMED,
        )

    def test_partial_fulfill_sets_partially_fulfilled(self):
        order = self._make_confirmed_order()
        order.fulfill_items({"1": 5})
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

    def test_partial_fulfill_tracks_shipped(self):
        order = self._make_confirmed_order()
        order.fulfill_items({"1": 5, "2": 3})
        w = order.items[0]
        g = order.items[1]
        assert w.shipped_quantity == 5
        assert w.remaining_quantity == 5
        assert g.shipped_quantity == 3
        assert g.remaining_quantity == 2

    def test_fulfill_all_items_sets_fulfilled(self):
        order = self._make_confirmed_order()
        order.fulfill_items({"1": 10, "2": 5})
        assert order.status == OrderStatus.FULFILLED

    def test_multi_step_fulfillment(self):
        order = self._make_confirmed_order()
        order.fulfill_items({"1": 3, "2": 2})
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

        order.fulfill_items({"1": 7, "2": 3})
        assert order.status == OrderStatus.FULFILLED

    def test_fulfill_items_from_partially_fulfilled_state(self):
        order = self._make_confirmed_order()
        order.fulfill_items({"1": 5})
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

        order.fulfill_items({"2": 5})
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

        order.fulfill_items({"1": 5})
        assert order.status == OrderStatus.FULFILLED

    def test_fulfill_items_draft_rejected(self):
        order = Order(
            id=1,
            customer_name="Bob",
            items=[OrderLineItem("1", "Widget", Quantity(5), Money.of("10.00"))],
            status=OrderStatus.DRAFT,
        )
        with pytest.raises(ValidationError, match="DRAFT"):
            order.fulfill_items({"1": 3})

    def test_fulfill_items_cancelled_rejected(self):
        order = Order(
            id=1,
            customer_name="Bob",
            items=[OrderLineItem("1", "Widget", Quantity(5), Money.of("10.00"))],
            status=OrderStatus.CANCELLED,
        )
        with pytest.raises(ValidationError, match="CANCELLED"):
            order.fulfill_items({"1": 3})

    def test_fulfill_items_already_fulfilled_rejected(self):
        order = self._make_confirmed_order()
        order.fulfill_items({"1": 10, "2": 5})
        with pytest.raises(ValidationError, match="already fulfilled"):
            order.fulfill_items({"1": 1})

    def test_fulfill_items_empty_quantities_rejected(self):
        order = self._make_confirmed_order()
        with pytest.raises(ValidationError, match="at least one item"):
            order.fulfill_items({})

    def test_fulfill_items_unknown_product_rejected(self):
        order = self._make_confirmed_order()
        with pytest.raises(ValidationError, match="not found"):
            order.fulfill_items({"999": 1})


# ── Order.fulfill() convenience — backwards compatibility ────────────────────


class TestOrderFulfillConvenience:

    def test_fulfill_ships_everything(self):
        order = Order(
            id=1,
            customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(10), Money.of("15.00")),
                OrderLineItem("2", "Gadget", Quantity(5), Money.of("25.00")),
            ],
            status=OrderStatus.CONFIRMED,
        )
        order.fulfill()
        assert order.status == OrderStatus.FULFILLED
        assert all(item.is_fully_shipped for item in order.items)

    def test_fulfill_from_partially_fulfilled(self):
        order = Order(
            id=1,
            customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(10), Money.of("15.00")),
                OrderLineItem("2", "Gadget", Quantity(5), Money.of("25.00")),
            ],
            status=OrderStatus.CONFIRMED,
        )
        order.fulfill_items({"1": 5})
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

        order.fulfill()  # fulfills remaining
        assert order.status == OrderStatus.FULFILLED
        assert order.items[0].shipped_quantity == 10
        assert order.items[1].shipped_quantity == 5


# ── Cancel PARTIALLY_FULFILLED ───────────────────────────────────────────────


class TestCancelPartiallyFulfilled:

    def test_cancel_partially_fulfilled_allowed(self):
        order = Order(
            id=1,
            customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(10), Money.of("15.00")),
                OrderLineItem("2", "Gadget", Quantity(5), Money.of("25.00")),
            ],
            status=OrderStatus.CONFIRMED,
        )
        order.fulfill_items({"1": 3, "2": 1})
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_preserves_shipped_history(self):
        order = Order(
            id=1,
            customer_name="Alice",
            items=[
                OrderLineItem("1", "Widget", Quantity(10), Money.of("15.00")),
                OrderLineItem("2", "Gadget", Quantity(5), Money.of("25.00")),
            ],
            status=OrderStatus.CONFIRMED,
        )
        order.fulfill_items({"1": 3, "2": 1})
        order.cancel()

        # Shipped quantities preserved
        assert order.items[0].shipped_quantity == 3
        assert order.items[1].shipped_quantity == 1


# ── Order.has_shipments ──────────────────────────────────────────────────────


class TestOrderHasShipments:

    def test_no_shipments(self):
        order = Order(
            id=1,
            customer_name="Alice",
            items=[OrderLineItem("1", "Widget", Quantity(5), Money.of("10.00"))],
            status=OrderStatus.CONFIRMED,
        )
        assert not order.has_shipments

    def test_has_shipments_after_partial_fulfill(self):
        order = Order(
            id=1,
            customer_name="Alice",
            items=[OrderLineItem("1", "Widget", Quantity(5), Money.of("10.00"))],
            status=OrderStatus.CONFIRMED,
        )
        order.fulfill_items({"1": 2})
        assert order.has_shipments
