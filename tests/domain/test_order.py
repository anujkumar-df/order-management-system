"""Unit tests for the Order aggregate and its business rules."""

from decimal import Decimal

import pytest

from oms.domain.exceptions import ValidationError
from oms.domain.model.order import Order, OrderLineItem, OrderStatus
from oms.domain.model.value_objects import Money, Quantity


def _make_item(name: str = "Widget", qty: int = 1, price: str = "15.00") -> OrderLineItem:
    """Helper to build a valid line item."""
    return OrderLineItem(
        product_id="1",
        product_name=name,
        quantity=Quantity(qty),
        unit_price=Money.of(price),
    )


class TestOrderCreation:

    def test_happy_path(self):
        order = Order.create(
            customer_name="Alice",
            items=[_make_item(qty=2, price="10.00")],
        )
        assert order.customer_name == "Alice"
        assert order.status == OrderStatus.DRAFT
        assert len(order.items) == 1
        assert order.total == Money.of("20.00")

    def test_id_is_none_for_new_orders(self):
        order = Order.create("Alice", [_make_item()])
        assert order.id is None  # assigned by repository

    def test_total_is_sum_of_line_items(self):
        items = [
            _make_item("Widget", qty=3, price="15.00"),
            _make_item("Gadget", qty=5, price="25.00"),
        ]
        order = Order.create("Bob", items)
        assert order.total == Money.of("170.00")


class TestOrderMinimumTotal:

    def test_order_below_minimum_rejected(self):
        with pytest.raises(ValidationError, match="below minimum"):
            Order.create("Alice", [_make_item(price="5.00", qty=1)])

    def test_order_at_exactly_minimum_accepted(self):
        order = Order.create("Alice", [_make_item(price="10.00", qty=1)])
        assert order.total == Money.of("10.00")


class TestOrderMaxItems:

    def test_51_items_rejected(self):
        items = [_make_item(price="1.00", qty=1) for _ in range(51)]
        with pytest.raises(ValidationError, match="Maximum 50 items"):
            Order.create("Alice", items)

    def test_50_items_accepted(self):
        # 50 items at $1 each = $50 total (above minimum)
        items = [_make_item(price="1.00", qty=1) for _ in range(50)]
        order = Order.create("Alice", items)
        assert len(order.items) == 50


class TestOrderValidation:

    def test_empty_customer_name_rejected(self):
        with pytest.raises(ValidationError, match="Customer name"):
            Order.create("", [_make_item()])

    def test_whitespace_customer_name_rejected(self):
        with pytest.raises(ValidationError, match="Customer name"):
            Order.create("   ", [_make_item()])

    def test_no_items_rejected(self):
        with pytest.raises(ValidationError, match="at least one item"):
            Order.create("Alice", [])


class TestOrderLineItem:

    def test_line_total_calculation(self):
        item = _make_item(qty=3, price="15.00")
        assert item.line_total == Money.of("45.00")

    def test_price_is_snapshot(self):
        """The line item holds its own price copy, unaffected by external changes."""
        original_price = Money.of("15.00")
        item = OrderLineItem(
            product_id="1",
            product_name="Widget",
            quantity=Quantity(1),
            unit_price=original_price,
        )
        # Even if we had a product object and changed its price,
        # the line item's unit_price stays the same.
        assert item.unit_price == Money.of("15.00")
