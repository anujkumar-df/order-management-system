"""Order aggregate — the core of the domain.

The Order is an aggregate root that owns its line items.
All business invariants are enforced here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from oms.domain.exceptions import ValidationError
from oms.domain.model.value_objects import Money, Quantity


class OrderStatus(Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class OrderLineItem:
    """A value object that captures the price snapshot of a product at
    the time the order was created.

    Frozen (immutable) because once an order is placed, the line items
    should not change without going through the aggregate root.
    """

    product_id: str
    product_name: str
    quantity: Quantity
    unit_price: Money  # locked at order-creation time

    @property
    def line_total(self) -> Money:
        return self.unit_price * self.quantity.value


# ---------------------------------------------------------------------------
# Constants for business rules
# ---------------------------------------------------------------------------
MIN_ORDER_TOTAL = Money(Decimal("10.00"))
MAX_LINE_ITEMS = 50


@dataclass
class Order:
    """Aggregate root for purchase orders.

    Use the ``Order.create()`` factory for new orders — it enforces all
    business rules.  The ``__init__`` is intentionally simple so the
    repository can reconstitute persisted orders without re-validating.
    """

    id: int | None
    customer_name: str
    items: list[OrderLineItem]
    status: OrderStatus = OrderStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # --- Factory (used for NEW orders only) -----------------------------------

    @staticmethod
    def create(
        customer_name: str,
        items: list[OrderLineItem],
    ) -> Order:
        """Create a new order, enforcing all invariants."""
        if not customer_name or not customer_name.strip():
            raise ValidationError("Customer name is required")

        if not items:
            raise ValidationError("Order must contain at least one item")

        if len(items) > MAX_LINE_ITEMS:
            raise ValidationError(f"Maximum {MAX_LINE_ITEMS} items per order")

        order = Order(id=None, customer_name=customer_name.strip(), items=list(items))

        # Validate minimum total
        if order.total < MIN_ORDER_TOTAL:
            raise ValidationError(
                f"Order total {order.total} below minimum {MIN_ORDER_TOTAL}"
            )

        return order

    # --- Computed properties --------------------------------------------------

    @property
    def total(self) -> Money:
        result = Money(Decimal("0.00"))
        for item in self.items:
            result = result + item.line_total
        return result
