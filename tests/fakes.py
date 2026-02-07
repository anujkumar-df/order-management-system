"""In-memory fake repositories for testing.

These implement the same abstract interfaces as the JSON repositories
but keep everything in a dict. No file I/O, no side effects.
"""

from __future__ import annotations

from oms.domain.model.inventory import InventoryItem
from oms.domain.model.order import Order
from oms.domain.model.product import Product
from oms.domain.repository.inventory_repository import InventoryRepository
from oms.domain.repository.order_repository import OrderRepository
from oms.domain.repository.product_repository import ProductRepository


class FakeOrderRepository(OrderRepository):

    def __init__(self) -> None:
        self._store: dict[int, Order] = {}
        self._next_id = 1

    def next_id(self) -> int:
        return self._next_id

    def get_by_id(self, order_id: int) -> Order | None:
        return self._store.get(order_id)

    def save(self, order: Order) -> None:
        if order.id is None:
            order.id = self._next_id
            self._next_id += 1
        self._store[order.id] = order


class FakeProductRepository(ProductRepository):

    def __init__(self, products: list[Product] | None = None) -> None:
        self._store: dict[str, Product] = {}
        for p in products or []:
            self._store[p.id] = p

    def get_by_id(self, product_id: str) -> Product | None:
        return self._store.get(product_id)

    def get_by_name(self, name: str) -> Product | None:
        for p in self._store.values():
            if p.name.lower() == name.lower():
                return p
        return None

    def list_all(self) -> list[Product]:
        return list(self._store.values())

    def save(self, product: Product) -> None:
        self._store[product.id] = product


class FakeInventoryRepository(InventoryRepository):

    def __init__(self, items: list[InventoryItem] | None = None) -> None:
        self._store: dict[str, InventoryItem] = {}
        for item in items or []:
            self._store[item.product_id] = item

    def get_by_product_id(self, product_id: str) -> InventoryItem | None:
        return self._store.get(product_id)

    def list_all(self) -> list[InventoryItem]:
        return list(self._store.values())

    def save(self, item: InventoryItem) -> None:
        self._store[item.product_id] = item
