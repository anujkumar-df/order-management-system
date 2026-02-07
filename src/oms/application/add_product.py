"""Application service: Add Product use case."""

from __future__ import annotations

from oms.domain.exceptions import ValidationError
from oms.domain.model.product import Product
from oms.domain.model.value_objects import Money
from oms.domain.repository.product_repository import ProductRepository


class AddProductHandler:

    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def handle(self, name: str, price: str) -> Product:
        """Add a new product to the catalog."""
        if not name or not name.strip():
            raise ValidationError("Product name is required")

        existing = self._product_repo.get_by_name(name)
        if existing is not None:
            raise ValidationError(f"Product '{name}' already exists")

        # Auto-assign ID based on existing products
        all_products = self._product_repo.list_all()
        if all_products:
            next_id = str(max(int(p.id) for p in all_products) + 1)
        else:
            next_id = "1"

        product = Product(id=next_id, name=name.strip(), price=Money.of(price))
        self._product_repo.save(product)
        return product
