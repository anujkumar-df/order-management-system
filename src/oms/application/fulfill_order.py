"""Application service: Fulfill Order use case.

Orchestrates the domain service (inventory fulfillment) and the
Order aggregate (state transition) to fulfill a confirmed order.
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

    def handle(self, order_id: int) -> None:
        order = self._order_repo.get_by_id(order_id)
        if order is None:
            raise EntityNotFoundError(f"Order #{order_id} not found")

        # Validate state transition first (fail fast before touching inventory)
        order.fulfill()

        # Permanently deduct the reserved inventory
        svc = InventoryReservationService(self._inventory_repo)
        svc.fulfill_for_order(order)

        self._order_repo.save(order)
