"""Integration tests for the ConfirmOrder use case."""

import pytest

from oms.application.confirm_order import ConfirmOrderHandler
from oms.application.create_order import CreateOrderHandler
from oms.application.dto import OrderItemSpec
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


class TestConfirmOrderHappyPath:

    def test_confirm_reserves_inventory(self):
        order_repo, product_repo, inventory_repo = _setup()

        # Create a draft order
        create = CreateOrderHandler(order_repo, product_repo)
        dto = create.handle("Alice", [OrderItemSpec("Widget", 10), OrderItemSpec("Gadget", 5)])

        # Confirm it
        confirm = ConfirmOrderHandler(order_repo, inventory_repo)
        confirm.handle(dto.id)

        # Order is now CONFIRMED
        order = order_repo.get_by_id(dto.id)
        assert order.status == OrderStatus.CONFIRMED

        # Inventory is reserved
        assert inventory_repo.get_by_product_id("1").reserved_quantity == 10
        assert inventory_repo.get_by_product_id("2").reserved_quantity == 5

    def test_confirm_nonexistent_order_rejected(self):
        order_repo, _, inventory_repo = _setup()
        handler = ConfirmOrderHandler(order_repo, inventory_repo)

        with pytest.raises(EntityNotFoundError, match="not found"):
            handler.handle(999)


class TestConfirmOrderValidation:

    def test_insufficient_inventory_rejected(self):
        order_repo, product_repo, inventory_repo = _setup()

        create = CreateOrderHandler(order_repo, product_repo)
        dto = create.handle("Bob", [OrderItemSpec("Widget", 95)])

        # Reserve 20 Widgets first to make only 80 available
        inv = inventory_repo.get_by_product_id("1")
        inv.reserve(20)
        inventory_repo.save(inv)

        confirm = ConfirmOrderHandler(order_repo, inventory_repo)
        with pytest.raises(ValidationError, match="Insufficient inventory for Widget"):
            confirm.handle(dto.id)

        # Order should still be DRAFT
        order = order_repo.get_by_id(dto.id)
        assert order.status == OrderStatus.DRAFT

    def test_confirm_already_confirmed_rejected(self):
        order_repo, product_repo, inventory_repo = _setup()

        create = CreateOrderHandler(order_repo, product_repo)
        dto = create.handle("Alice", [OrderItemSpec("Widget", 1)])

        confirm = ConfirmOrderHandler(order_repo, inventory_repo)
        confirm.handle(dto.id)

        with pytest.raises(ValidationError, match="expected DRAFT"):
            confirm.handle(dto.id)
