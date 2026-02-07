"""Application service: Set Inventory use case."""

from __future__ import annotations

from oms.domain.exceptions import EntityNotFoundError
from oms.domain.model.inventory import InventoryItem
from oms.domain.repository.inventory_repository import InventoryRepository
from oms.domain.repository.product_repository import ProductRepository


class SetInventoryHandler:

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        product_repo: ProductRepository,
    ) -> None:
        self._inventory_repo = inventory_repo
        self._product_repo = product_repo

    def handle(self, product_name: str, quantity: int) -> None:
        """Set the total inventory quantity for a product."""
        product = self._product_repo.get_by_name(product_name)
        if product is None:
            raise EntityNotFoundError(f"Product not found: '{product_name}'")

        existing = self._inventory_repo.get_by_product_id(product.id)
        if existing is not None:
            existing.total_quantity = quantity
            self._inventory_repo.save(existing)
        else:
            item = InventoryItem(
                product_id=product.id,
                product_name=product.name,
                total_quantity=quantity,
            )
            self._inventory_repo.save(item)
