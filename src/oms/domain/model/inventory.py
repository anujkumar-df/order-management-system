"""InventoryItem aggregate — tracks stock and reservations per product.

Each product has one InventoryItem that knows the total quantity in stock
and how much of it has been reserved by confirmed orders.
"""

from __future__ import annotations

from dataclasses import dataclass

from oms.domain.exceptions import ValidationError


@dataclass
class InventoryItem:
    """Aggregate root for inventory tracking.

    Invariants:
    - ``reserved_quantity`` can never exceed ``total_quantity``
    - ``available_quantity`` is always >= 0
    """

    product_id: str
    product_name: str
    total_quantity: int
    reserved_quantity: int = 0

    @property
    def available_quantity(self) -> int:
        return self.total_quantity - self.reserved_quantity

    def reserve(self, quantity: int) -> None:
        """Reserve stock for a confirmed order.

        Raises ValidationError if insufficient inventory is available.
        """
        if quantity <= 0:
            raise ValidationError("Reservation quantity must be positive")
        if quantity > self.available_quantity:
            raise ValidationError(
                f"Insufficient inventory for {self.product_name} "
                f"(need {quantity}, have {self.available_quantity} available)"
            )
        self.reserved_quantity += quantity

    def release(self, quantity: int) -> None:
        """Release previously reserved stock (e.g. on order cancellation)."""
        if quantity <= 0:
            raise ValidationError("Release quantity must be positive")
        if quantity > self.reserved_quantity:
            raise ValidationError(
                f"Cannot release {quantity} of {self.product_name} "
                f"— only {self.reserved_quantity} currently reserved"
            )
        self.reserved_quantity -= quantity

    def fulfill(self, quantity: int) -> None:
        """Permanently deduct fulfilled stock.

        Moves items from reserved to shipped — both ``total_quantity``
        and ``reserved_quantity`` decrease by the same amount.
        """
        if quantity <= 0:
            raise ValidationError("Fulfill quantity must be positive")
        if quantity > self.reserved_quantity:
            raise ValidationError(
                f"Cannot fulfill {quantity} of {self.product_name} "
                f"— only {self.reserved_quantity} currently reserved"
            )
        self.reserved_quantity -= quantity
        self.total_quantity -= quantity
