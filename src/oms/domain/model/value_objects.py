"""Value Objects shared across the domain.

Value Objects are immutable and compared by value, not identity.
They encapsulate validation so invalid values can never exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from oms.domain.exceptions import ValidationError


@dataclass(frozen=True)
class Money:
    """Monetary amount with currency.

    Uses Decimal to avoid floating-point rounding errors that would be
    unacceptable in financial calculations.
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise ValidationError(
                f"Money amount must be a Decimal, got {type(self.amount).__name__}"
            )
        if self.amount < Decimal("0"):
            raise ValidationError(
                f"Money amount cannot be negative, got {self.amount}"
            )

    # --- Arithmetic helpers ---------------------------------------------------

    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        result = self.amount - other.amount
        if result < Decimal("0"):
            raise ValidationError("Money subtraction would result in a negative amount")
        return Money(result, self.currency)

    def __mul__(self, factor: int) -> Money:
        if not isinstance(factor, int):
            raise TypeError(f"Can only multiply Money by int, got {type(factor).__name__}")
        return Money(self.amount * factor, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount >= other.amount

    # --- Display --------------------------------------------------------------

    def __str__(self) -> str:
        return f"${self.amount:.2f}"

    # --- Internal helpers -----------------------------------------------------

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValidationError(
                f"Cannot combine {self.currency} with {other.currency}"
            )

    # --- Factory --------------------------------------------------------------

    @staticmethod
    def of(amount: str | float | int | Decimal) -> Money:
        """Convenient factory that coerces to Decimal safely."""
        try:
            return Money(Decimal(str(amount)))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid money amount: {amount!r}") from exc


@dataclass(frozen=True)
class Quantity:
    """A positive integer quantity.

    Enforces the invariant that you cannot order zero or negative items.
    """

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise ValidationError(
                f"Quantity must be an integer, got {type(self.value).__name__}"
            )
        if self.value <= 0:
            raise ValidationError("Quantity must be positive")

    def __str__(self) -> str:
        return str(self.value)
