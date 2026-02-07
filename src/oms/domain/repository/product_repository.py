"""Abstract repository for Product aggregate.

Defined in the domain layer so the domain never depends on
infrastructure. Concrete implementations (JSON, SQL, in-memory)
live in the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from oms.domain.model.product import Product


class ProductRepository(ABC):

    @abstractmethod
    def get_by_id(self, product_id: str) -> Product | None:
        """Return a product by its ID, or None if not found."""

    @abstractmethod
    def get_by_name(self, name: str) -> Product | None:
        """Return a product by its exact name, or None if not found."""

    @abstractmethod
    def list_all(self) -> list[Product]:
        """Return every product in the catalog."""

    @abstractmethod
    def save(self, product: Product) -> None:
        """Persist a new or updated product."""
