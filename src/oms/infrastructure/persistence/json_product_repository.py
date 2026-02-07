"""JSON-file-backed implementation of ProductRepository."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from oms.domain.model.product import Product
from oms.domain.model.value_objects import Money
from oms.domain.repository.product_repository import ProductRepository


class JsonProductRepository(ProductRepository):

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._ensure_file()

    # --- ProductRepository interface ------------------------------------------

    def get_by_id(self, product_id: str) -> Product | None:
        products = self._load()
        return products.get(product_id)

    def get_by_name(self, name: str) -> Product | None:
        for product in self._load().values():
            if product.name.lower() == name.lower():
                return product
        return None

    def list_all(self) -> list[Product]:
        return list(self._load().values())

    def save(self, product: Product) -> None:
        products = self._load()
        products[product.id] = product
        self._persist(products)

    # --- Serialization helpers ------------------------------------------------

    def _load(self) -> dict[str, Product]:
        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        return {
            item["id"]: Product(
                id=item["id"],
                name=item["name"],
                price=Money(Decimal(item["price"]), item.get("currency", "USD")),
            )
            for item in raw
        }

    def _persist(self, products: dict[str, Product]) -> None:
        raw = [
            {
                "id": p.id,
                "name": p.name,
                "price": str(p.price.amount),
                "currency": p.price.currency,
            }
            for p in products.values()
        ]
        self._file_path.write_text(
            json.dumps(raw, indent=2) + "\n", encoding="utf-8"
        )

    def _ensure_file(self) -> None:
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text("[]", encoding="utf-8")
