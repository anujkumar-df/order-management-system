"""Domain service: Inventory Reservation.

This service coordinates the cross-aggregate operation of reserving
or releasing inventory for an order.  It lives in the domain layer
because the logic is a core business rule, not just orchestration.

The two-phase approach (validate-then-mutate) ensures we never leave
inventory in a partially-reserved state if one product fails validation.
"""

from __future__ import annotations

from oms.domain.exceptions import EntityNotFoundError, ValidationError
from oms.domain.model.inventory import InventoryItem
from oms.domain.model.order import Order
from oms.domain.repository.inventory_repository import InventoryRepository


class InventoryReservationService:

    def __init__(self, inventory_repo: InventoryRepository) -> None:
        self._inventory_repo = inventory_repo

    def reserve_for_order(self, order: Order) -> None:
        """Reserve inventory for every line item in the order.

        Uses a two-phase approach:
          Phase 1 — load and validate: ensure every product has enough
                    available stock.  Fails fast before any mutation.
          Phase 2 — mutate and persist: call ``reserve()`` on each
                    InventoryItem and save.
        """
        # Phase 1: load all inventory items and validate
        inventory_items: list[tuple[InventoryItem, int]] = []

        for line in order.items:
            inv = self._inventory_repo.get_by_product_id(line.product_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"No inventory record for product '{line.product_name}'"
                )
            qty = line.quantity.value
            if qty > inv.available_quantity:
                raise ValidationError(
                    f"Insufficient inventory for {line.product_name} "
                    f"(need {qty}, have {inv.available_quantity} available)"
                )
            inventory_items.append((inv, qty))

        # Phase 2: mutate and persist
        for inv, qty in inventory_items:
            inv.reserve(qty)
            self._inventory_repo.save(inv)

    def release_for_order(self, order: Order) -> None:
        """Release previously reserved inventory for an order."""
        for line in order.items:
            inv = self._inventory_repo.get_by_product_id(line.product_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"No inventory record for product '{line.product_name}'"
                )
            inv.release(line.quantity.value)
            self._inventory_repo.save(inv)

    def fulfill_for_order(self, order: Order) -> None:
        """Permanently deduct reserved inventory for a fulfilled order.

        For each line item, calls ``fulfill()`` on the InventoryItem which
        reduces both ``reserved_quantity`` and ``total_quantity``.
        """
        for line in order.items:
            inv = self._inventory_repo.get_by_product_id(line.product_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"No inventory record for product '{line.product_name}'"
                )
            inv.fulfill(line.quantity.value)
            self._inventory_repo.save(inv)
