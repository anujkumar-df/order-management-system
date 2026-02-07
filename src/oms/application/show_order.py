"""Application service: Show Order use case (query)."""

from __future__ import annotations

from oms.application.dto import OrderDTO, OrderLineItemDTO
from oms.domain.exceptions import EntityNotFoundError
from oms.domain.model.order import Order
from oms.domain.repository.order_repository import OrderRepository


class ShowOrderHandler:

    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo = order_repo

    def handle(self, order_id: int) -> OrderDTO:
        order = self._order_repo.get_by_id(order_id)
        if order is None:
            raise EntityNotFoundError(f"Order #{order_id} not found")
        return self._to_dto(order)

    @staticmethod
    def _to_dto(order: Order) -> OrderDTO:
        return OrderDTO(
            id=order.id,  # type: ignore[arg-type]
            customer_name=order.customer_name,
            status=order.status.value,
            items=[
                OrderLineItemDTO(
                    product_name=item.product_name,
                    quantity=item.quantity.value,
                    unit_price=str(item.unit_price),
                    line_total=str(item.line_total),
                )
                for item in order.items
            ],
            total=str(order.total),
            created_at=order.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        )
