"""Application service: Update Product use case."""

from __future__ import annotations

from oms.domain.exceptions import EntityNotFoundError
from oms.domain.model.value_objects import Money
from oms.domain.repository.product_repository import ProductRepository


class UpdateProductHandler:

    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def handle(self, product_id: str, new_price: str) -> None:
        """Update a product's price.

        This does NOT affect any existing orders — they captured a
        price snapshot at creation time.
        """
        product = self._product_repo.get_by_id(product_id)
        if product is None:
            raise EntityNotFoundError(f"Product with ID '{product_id}' not found")

        product.update_price(Money.of(new_price))
        self._product_repo.save(product)
