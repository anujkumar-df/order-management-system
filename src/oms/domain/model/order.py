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
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


@dataclass
class OrderLineItem:
    """Captures the price snapshot of a product at order-creation time.

    Mutable only via ``ship()`` which tracks how many units have been
    shipped.  The original ``quantity`` and ``unit_price`` never change
    (price lock preserved).
    """

    product_id: str
    product_name: str
    quantity: Quantity
    unit_price: Money  # locked at order-creation time
    shipped_quantity: int = 0

    @property
    def line_total(self) -> Money:
        return self.unit_price * self.quantity.value

    @property
    def remaining_quantity(self) -> int:
        return self.quantity.value - self.shipped_quantity

    @property
    def is_fully_shipped(self) -> bool:
        return self.remaining_quantity == 0

    def ship(self, qty: int) -> None:
        """Record that *qty* units have been shipped."""
        if qty <= 0:
            raise ValidationError("Ship quantity must be positive")
        if qty > self.remaining_quantity:
            raise ValidationError(
                f"Cannot ship {qty} of {self.product_name} "
                f"— only {self.remaining_quantity} remaining"
            )
        self.shipped_quantity += qty


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

    # --- State transitions ----------------------------------------------------

    def confirm(self) -> None:
        """Transition DRAFT -> CONFIRMED.

        Inventory reservation must happen *before* calling this
        (coordinated by the application handler via the domain service).
        """
        if self.status != OrderStatus.DRAFT:
            raise ValidationError(
                f"Cannot confirm order — current status is {self.status.value}, "
                f"expected DRAFT"
            )
        self.status = OrderStatus.CONFIRMED

    def fulfill(self) -> None:
        """Fulfill all remaining items at once (convenience method).

        Backwards compatible with Flow 3. Delegates to ``fulfill_items``
        with all remaining quantities.
        """
        remaining = {
            item.product_id: item.remaining_quantity
            for item in self.items
            if item.remaining_quantity > 0
        }
        self.fulfill_items(remaining)

    def fulfill_items(self, quantities: dict[str, int]) -> None:
        """Fulfill specific quantities per product.

        Handles both full and partial fulfillment:
        - If all items are fully shipped afterwards -> FULFILLED
        - Otherwise -> PARTIALLY_FULFILLED

        Inventory fulfillment (deducting stock) must happen separately
        via the domain service.
        """
        if self.status == OrderStatus.FULFILLED:
            raise ValidationError("Order already fulfilled")
        if self.status not in (OrderStatus.CONFIRMED, OrderStatus.PARTIALLY_FULFILLED):
            raise ValidationError(
                f"Cannot fulfill order in {self.status.value} status"
            )

        if not quantities:
            raise ValidationError("Must specify at least one item to fulfill")

        # Ship each specified quantity
        for product_id, qty in quantities.items():
            item = self._find_item(product_id)
            item.ship(qty)

        # Auto-resolve status
        if all(item.is_fully_shipped for item in self.items):
            self.status = OrderStatus.FULFILLED
        else:
            self.status = OrderStatus.PARTIALLY_FULFILLED

    def cancel(self) -> None:
        """Transition DRAFT|CONFIRMED|PARTIALLY_FULFILLED -> CANCELLED.

        If the order was CONFIRMED or PARTIALLY_FULFILLED, inventory
        release must happen *before* calling this (for remaining
        reserved quantities only).
        """
        if self.status == OrderStatus.CANCELLED:
            raise ValidationError("Order is already cancelled")
        if self.status == OrderStatus.FULFILLED:
            raise ValidationError("Cannot cancel order in FULFILLED status")
        self.status = OrderStatus.CANCELLED

    # --- Computed properties --------------------------------------------------

    @property
    def total(self) -> Money:
        result = Money(Decimal("0.00"))
        for item in self.items:
            result = result + item.line_total
        return result

    @property
    def has_shipments(self) -> bool:
        """True if any items have been partially or fully shipped."""
        return any(item.shipped_quantity > 0 for item in self.items)

    # --- Internal helpers -----------------------------------------------------

    def _find_item(self, product_id: str) -> OrderLineItem:
        for item in self.items:
            if item.product_id == product_id:
                return item
        raise ValidationError(f"Product ID '{product_id}' not found in this order")
