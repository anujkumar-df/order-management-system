"""Integration tests for the FulfillOrder use case."""

import pytest

from oms.application.confirm_order import ConfirmOrderHandler
from oms.application.create_order import CreateOrderHandler
from oms.application.dto import OrderItemSpec
from oms.application.fulfill_order import FulfillOrderHandler
from oms.domain.exceptions import EntityNotFoundError, ValidationError
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


class TestFulfillOrderHappyPath:

    def test_fulfill_deducts_inventory(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 20), OrderItemSpec("Gadget", 10)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid)

        order = order_repo.get_by_id(oid)
        assert order.status == OrderStatus.FULFILLED

        w = inventory_repo.get_by_product_id("1")
        assert w.total_quantity == 80
        assert w.reserved_quantity == 0
        assert w.available_quantity == 80

        g = inventory_repo.get_by_product_id("2")
        assert g.total_quantity == 40
        assert g.reserved_quantity == 0
        assert g.available_quantity == 40


class TestFulfillOrderValidation:

    def test_fulfill_draft_rejected(self):
        order_repo, product_repo, inventory_repo = _setup()
        create = CreateOrderHandler(order_repo, product_repo)
        dto = create.handle("Bob", [OrderItemSpec("Widget", 5)])

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        with pytest.raises(ValidationError, match="DRAFT"):
            fulfill.handle(dto.id)

    def test_fulfill_nonexistent_order_rejected(self):
        order_repo, _, inventory_repo = _setup()
        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        with pytest.raises(EntityNotFoundError, match="not found"):
            fulfill.handle(999)

    def test_fulfill_already_fulfilled_rejected(self):
        order_repo, product_repo, inventory_repo = _setup()
        oid = _create_and_confirm(
            order_repo, product_repo, inventory_repo,
            [OrderItemSpec("Widget", 5)],
        )

        fulfill = FulfillOrderHandler(order_repo, inventory_repo)
        fulfill.handle(oid)

        with pytest.raises(ValidationError, match="already fulfilled"):
            fulfill.handle(oid)
