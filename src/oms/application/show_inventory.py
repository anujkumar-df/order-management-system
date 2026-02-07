"""Application service: Show Inventory use case (query)."""

from __future__ import annotations

from dataclasses import dataclass

from oms.domain.repository.inventory_repository import InventoryRepository


@dataclass(frozen=True)
class InventoryLineDTO:
    product_name: str
    total: int
    reserved: int
    available: int


class ShowInventoryHandler:

    def __init__(self, inventory_repo: InventoryRepository) -> None:
        self._inventory_repo = inventory_repo

    def handle(self) -> list[InventoryLineDTO]:
        items = self._inventory_repo.list_all()
        return [
            InventoryLineDTO(
                product_name=item.product_name,
                total=item.total_quantity,
                reserved=item.reserved_quantity,
                available=item.available_quantity,
            )
            for item in items
        ]
