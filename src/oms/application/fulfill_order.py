"""Application service: Fulfill Order use case.

Orchestrates the domain service (inventory fulfillment) and the
Order aggregate (state transition) to fulfill a confirmed order,
either fully or partially.
"""

from __future__ import annotations

from oms.domain.exceptions import EntityNotFoundError
from oms.domain.repository.inventory_repository import InventoryRepository
from oms.domain.repository.order_repository import OrderRepository
from oms.domain.service.inventory_reservation_service import (
    InventoryReservationService,
)


class FulfillOrderHandler:

    def __init__(
        self,
        order_repo: OrderRepository,
        inventory_repo: InventoryRepository,
    ) -> None:
        self._order_repo = order_repo
        self._inventory_repo = inventory_repo

    def handle(
        self,
        order_id: int,
        partial_items: dict[str, int] | None = None,
    ) -> None:
        """Fulfill an order, fully or partially.

        Args:
            order_id: The order to fulfill.
            partial_items: If provided, a mapping of product_name -> quantity
                to ship. If None, fulfills all remaining items.
        """
        order = self._order_repo.get_by_id(order_id)
        if order is None:
            raise EntityNotFoundError(f"Order #{order_id} not found")

        svc = InventoryReservationService(self._inventory_repo)

        if partial_items is not None:
            # Resolve product names to IDs
            quantities = self._resolve_names_to_ids(order, partial_items)
        else:
            # Full fulfill — compute all remaining quantities
            quantities = {
                item.product_id: item.remaining_quantity
                for item in order.items
                if item.remaining_quantity > 0
            }

        # Ship on the order aggregate (updates shipped_quantity, status)
        order.fulfill_items(quantities)

        # Deduct from inventory
        svc.fulfill_items(quantities)

        self._order_repo.save(order)

    @staticmethod
    def _resolve_names_to_ids(
        order, name_quantities: dict[str, int]
    ) -> dict[str, int]:
        """Map product names to product IDs using the order's line items."""
        result: dict[str, int] = {}
        for name, qty in name_quantities.items():
            found = False
            for item in order.items:
                if item.product_name.lower() == name.lower():
                    result[item.product_id] = qty
                    found = True
                    break
            if not found:
                from oms.domain.exceptions import ValidationError

                raise ValidationError(
                    f"Product '{name}' not found in order #{order.id}"
                )
        return result
