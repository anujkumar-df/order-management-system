"""Abstract repository for InventoryItem aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod

from oms.domain.model.inventory import InventoryItem


class InventoryRepository(ABC):

    @abstractmethod
    def get_by_product_id(self, product_id: str) -> InventoryItem | None:
        """Return the inventory record for a product, or None."""

    @abstractmethod
    def list_all(self) -> list[InventoryItem]:
        """Return every inventory record."""

    @abstractmethod
    def save(self, item: InventoryItem) -> None:
        """Persist a new or updated inventory record."""
