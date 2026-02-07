"""Application service: Cancel Order use case.

If the order was CONFIRMED or PARTIALLY_FULFILLED, releases remaining
reserved inventory before cancelling.  DRAFT orders can be cancelled
without inventory changes.

For PARTIALLY_FULFILLED orders, only the *unshipped* reserved quantities
are released; shipped items are preserved as a historical record.
"""

from __future__ import annotations

from oms.domain.exceptions import EntityNotFoundError
from oms.domain.model.order import OrderStatus
from oms.domain.repository.inventory_repository import InventoryRepository
from oms.domain.repository.order_repository import OrderRepository
from oms.domain.service.inventory_reservation_service import (
    InventoryReservationService,
)


class CancelOrderHandler:

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

        # Release inventory if the order had reserved it.
        # For PARTIALLY_FULFILLED, release_for_order uses remaining_quantity
        # (unshipped items only).
        if order.status in (OrderStatus.CONFIRMED, OrderStatus.PARTIALLY_FULFILLED):
            svc = InventoryReservationService(self._inventory_repo)
            svc.release_for_order(order)

        order.cancel()
        self._order_repo.save(order)
