"""Application service: Create Order use case.

Orchestrates the flow between repositories and the domain model.
This is the only place that coordinates multiple aggregates (Product
lookup + Order creation).
"""

from __future__ import annotations

from oms.application.dto import OrderDTO, OrderItemSpec, OrderLineItemDTO
from oms.domain.exceptions import EntityNotFoundError
from oms.domain.model.order import Order, OrderLineItem
from oms.domain.model.value_objects import Quantity
from oms.domain.repository.order_repository import OrderRepository
from oms.domain.repository.product_repository import ProductRepository


class CreateOrderHandler:

    def __init__(
        self,
        order_repo: OrderRepository,
        product_repo: ProductRepository,
    ) -> None:
        self._order_repo = order_repo
        self._product_repo = product_repo

    def handle(self, customer_name: str, item_specs: list[OrderItemSpec]) -> OrderDTO:
        """Create a new purchase order.

        Steps:
        1. Resolve each product name to a Product (fail if not found).
        2. Build OrderLineItems with *current* prices (snapshot).
        3. Let the Order aggregate validate all business rules.
        4. Persist and return a DTO.
        """
        line_items: list[OrderLineItem] = []

        for spec in item_specs:
            product = self._product_repo.get_by_name(spec.product_name)
            if product is None:
                raise EntityNotFoundError(
                    f"Product not found: '{spec.product_name}'"
                )

            line_items.append(
                OrderLineItem(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=Quantity(spec.quantity),
                    unit_price=product.price,  # <-- price snapshot
                )
            )

        order = Order.create(customer_name=customer_name, items=line_items)
        self._order_repo.save(order)

        return self._to_dto(order)

    # --- Mapping --------------------------------------------------------------

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
