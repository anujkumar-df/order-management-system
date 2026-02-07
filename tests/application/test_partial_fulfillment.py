"""Integration tests for partial fulfillment use cases."""

import pytest

from oms.application.cancel_order import CancelOrderHandler
from oms.application.confirm_order import ConfirmOrderHandler
from oms.application.create_order import CreateOrderHandler
from oms.application.dto import OrderItemSpec
from oms.application.fulfill_order import FulfillOrderHandler
from oms.application.show_order import ShowOrderHandler
from oms.domain.exceptions import ValidationError
from oms.domain.model.inventory import InventoryItem
from oms.domain.model.order import OrderStatus
from oms.domain.model.product import Product
from oms.domain.model.value_objects import Money
from tests.fakes import FakeInventoryRepository, FakeOrderRepository, FakeProductRepository


def _setup():
    products = [
        Product(id="1", name="Widget", price=Money.of("15.00")),
        Product(id="2", name="Gadget", price=Money.of("25.00")),
    ]
    inventory = [
        InventoryItem(product_id="1", product_name="Widget", total_quantity=100),
        InventoryItem(product_id="2", product_name="Gadget", total_quantity=50),
    ]
    order_repo = FakeOrderRepository()
    product_repo = FakeProductRepository(products)
    inventory_repo = FakeInventoryRepository(inventory)
    return order_repo, product_repo, inventory_repo


def _create_and_confirm(order_repo, product_repo, inventory_repo, items):
    """Helper: create a draft order and confirm it."""
    create = CreateOrderHandler(order_repo, product_repo)
    dto = create.handle("Alice", items)
    confirm = ConfirmOrderHandler(order_repo, inventory_repo)
    confirm.handle(dto.id)
    return dto.id


# ── Partial Fulfillment Happy Path ───────────────────────────────────────────


class TestPartialFulfillHappyPath:

    def test_partial_fulfill_updates_status_and_inventory(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 30), OrderItemSpec("Gadget", 15)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid, partial_items={"Widget": 20, "Gadget": 10})

        order = order_repo.get_by_id(oid)
        assert order.status == OrderStatus.PARTIALLY_FULFILLED

        # Widget: shipped 20, remaining 10 reserved
        w = inventory_repo.get_by_product_id("1")
        assert w.total_quantity == 80   # 100 - 20 shipped
        assert w.reserved_quantity == 10  # 30 - 20 shipped
        assert w.available_quantity == 70

        # Gadget: shipped 10, remaining 5 reserved
        g = inventory_repo.get_by_product_id("2")
        assert g.total_quantity == 40   # 50 - 10 shipped
        assert g.reserved_quantity == 5   # 15 - 10 shipped
        assert g.available_quantity == 35

    def test_complete_partial_fulfillment(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 30), OrderItemSpec("Gadget", 15)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)

        # First partial
        fulfill.handle(oid, partial_items={"Widget": 20, "Gadget": 10})
        assert order_repo.get_by_id(oid).status == OrderStatus.PARTIALLY_FULFILLED

        # Second partial (completes it)
        fulfill.handle(oid, partial_items={"Widget": 10, "Gadget": 5})
        assert order_repo.get_by_id(oid).status == OrderStatus.FULFILLED

        # All inventory deducted
        w = inventory_repo.get_by_product_id("1")
        assert w.total_quantity == 70
        assert w.reserved_quantity == 0

        g = inventory_repo.get_by_product_id("2")
        assert g.total_quantity == 35
        assert g.reserved_quantity == 0

    def test_partial_fulfill_single_product(self):
        """Fulfill only some items of one product, leaving others untouched."""
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 10), OrderItemSpec("Gadget", 5)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid, partial_items={"Widget": 5})

        order = order_repo.get_by_id(oid)
        assert order.status == OrderStatus.PARTIALLY_FULFILLED
        assert order.items[0].shipped_quantity == 5
        assert order.items[1].shipped_quantity == 0


# ── Full Fulfill Backwards Compatibility ─────────────────────────────────────


class TestFullFulfillBackwardsCompat:

    def test_fulfill_without_partial_ships_everything(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 20), OrderItemSpec("Gadget", 10)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid)  # no partial_items

        order = order_repo.get_by_id(oid)
        assert order.status == OrderStatus.FULFILLED
        assert all(item.is_fully_shipped for item in order.items)

    def test_fulfill_remaining_from_partially_fulfilled(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 10), OrderItemSpec("Gadget", 5)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid, partial_items={"Widget": 5})
        assert order_repo.get_by_id(oid).status == OrderStatus.PARTIALLY_FULFILLED

        # Full fulfill ships remaining
        fulfill.handle(oid)
        order = order_repo.get_by_id(oid)
        assert order.status == OrderStatus.FULFILLED
        assert order.items[0].shipped_quantity == 10
        assert order.items[1].shipped_quantity == 5


# ── Cancel Partially Fulfilled Order ─────────────────────────────────────────


class TestCancelPartiallyFulfilledOrder:

    def test_cancel_releases_only_remaining_reserved(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 10), OrderItemSpec("Gadget", 6)],
        )

        # Partial fulfill
        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid, partial_items={"Widget": 4, "Gadget": 2})

        # Cancel
        cancel = CancelOrderHandler(order_repo, inventory_repo)
        cancel.handle(oid)

        order = order_repo.get_by_id(oid)
        assert order.status == OrderStatus.CANCELLED

        # Shipped history preserved
        assert order.items[0].shipped_quantity == 4
        assert order.items[1].shipped_quantity == 2

        # Widget: total was 100, shipped 4 -> 96; reserved was 10, shipped 4 -> 6 reserved, then released 6
        w = inventory_repo.get_by_product_id("1")
        assert w.total_quantity == 96
        assert w.reserved_quantity == 0
        assert w.available_quantity == 96

        # Gadget: total was 50, shipped 2 -> 48; reserved was 6, shipped 2 -> 4 reserved, then released 4
        g = inventory_repo.get_by_product_id("2")
        assert g.total_quantity == 48
        assert g.reserved_quantity == 0
        assert g.available_quantity == 48


# ── Partial Fulfill Validation ───────────────────────────────────────────────


class TestPartialFulfillValidation:

    def test_partial_fulfill_unknown_product_rejected(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 10)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        with pytest.raises(ValidationError, match="not found"):
            fulfill.handle(oid, partial_items={"Nonexistent": 5})

    def test_partial_fulfill_more_than_remaining_rejected(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 10)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        with pytest.raises(ValidationError, match="remaining"):
            fulfill.handle(oid, partial_items={"Widget": 15})


# ── ShowOrder DTO with shipment data ─────────────────────────────────────────


class TestShowOrderWithShipments:

    def test_show_order_includes_shipped_quantities(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 10), OrderItemSpec("Gadget", 5)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid, partial_items={"Widget": 6, "Gadget": 2})

        show = ShowOrderHandler(order_repo)
        dto = show.handle(oid)

        assert dto.status == "PARTIALLY_FULFILLED"
        assert dto.has_shipments

        assert dto.items[0].shipped_quantity == 6
        assert dto.items[0].remaining_quantity == 4
        assert dto.items[1].shipped_quantity == 2
        assert dto.items[1].remaining_quantity == 3

    def test_show_order_no_shipments(self):
        order_repo, product_repo, inventory_repo = _setup()
        create = CreateOrderHandler(order_repo, product_repo)
        dto = create.handle("Bob", [OrderItemSpec("Widget", 5)])

        show = ShowOrderHandler(order_repo)
        dto = show.handle(dto.id)

        assert not dto.has_shipments
        assert dto.items[0].shipped_quantity == 0
        assert dto.items[0].remaining_quantity == 5
