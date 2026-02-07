"""Integration tests for the CreateOrder use case.

Uses in-memory fake repositories — no file I/O.
"""

import pytest

from oms.application.create_order import CreateOrderHandler
from oms.application.dto import OrderItemSpec
from oms.domain.exceptions import EntityNotFoundError, ValidationError
from oms.domain.model.product import Product
from oms.domain.model.value_objects import Money
from tests.fakes import FakeOrderRepository, FakeProductRepository


def _setup(
    products: list[Product] | None = None,
) -> tuple[CreateOrderHandler, FakeOrderRepository, FakeProductRepository]:
    """Build handler with fake repos, optionally pre-loaded with products."""
    if products is None:
        products = [
            Product(id="1", name="Widget", price=Money.of("15.00")),
            Product(id="2", name="Gadget", price=Money.of("25.00")),
            Product(id="3", name="CheapItem", price=Money.of("5.00")),
        ]
    order_repo = FakeOrderRepository()
    product_repo = FakeProductRepository(products)
    handler = CreateOrderHandler(order_repo, product_repo)
    return handler, order_repo, product_repo


class TestCreateOrderHappyPath:

    def test_creates_order_with_correct_total(self):
        handler, order_repo, _ = _setup()
        dto = handler.handle("Alice", [
            OrderItemSpec("Widget", 3),
            OrderItemSpec("Gadget", 5),
        ])
        assert dto.total == "$170.00"
        assert dto.status == "DRAFT"
        assert dto.customer_name == "Alice"
        assert len(dto.items) == 2

    def test_assigns_order_id(self):
        handler, _, _ = _setup()
        dto = handler.handle("Alice", [OrderItemSpec("Widget", 1)])
        assert dto.id == 1

    def test_persists_order(self):
        handler, order_repo, _ = _setup()
        dto = handler.handle("Alice", [OrderItemSpec("Widget", 1)])
        saved = order_repo.get_by_id(dto.id)
        assert saved is not None
        assert saved.customer_name == "Alice"

    def test_sequential_ids(self):
        handler, _, _ = _setup()
        dto1 = handler.handle("Alice", [OrderItemSpec("Widget", 1)])
        dto2 = handler.handle("Bob", [OrderItemSpec("Gadget", 1)])
        assert dto2.id == dto1.id + 1


class TestCreateOrderPriceLock:

    def test_price_snapshot_at_creation(self):
        handler, order_repo, product_repo = _setup()

        # Create order at current price
        dto = handler.handle("Alice", [OrderItemSpec("Widget", 1)])
        assert dto.total == "$15.00"

        # Change the product price
        widget = product_repo.get_by_name("Widget")
        widget.update_price(Money.of("99.99"))
        product_repo.save(widget)

        # Existing order still has original price
        saved = order_repo.get_by_id(dto.id)
        assert str(saved.total) == "$15.00"


class TestCreateOrderValidation:

    def test_unknown_product_rejected(self):
        handler, _, _ = _setup()
        with pytest.raises(EntityNotFoundError, match="Product not found"):
            handler.handle("Alice", [OrderItemSpec("NonExistent", 1)])

    def test_below_minimum_rejected(self):
        handler, _, _ = _setup()
        with pytest.raises(ValidationError, match="below minimum"):
            handler.handle("Alice", [OrderItemSpec("CheapItem", 1)])

    def test_negative_quantity_rejected(self):
        handler, _, _ = _setup()
        with pytest.raises(ValidationError, match="must be positive"):
            handler.handle("Alice", [OrderItemSpec("Widget", -1)])
