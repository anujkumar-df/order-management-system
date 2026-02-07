"""Product aggregate.

Products live independently of orders. They have their own lifecycle:
prices change, products are added and removed from the catalog.
"""

from __future__ import annotations

from dataclasses import dataclass

from oms.domain.exceptions import ValidationError
from oms.domain.model.value_objects import Money


@dataclass
class Product:
    """A product in the catalog.

    This is an aggregate root — it is the entry point for any
    operation involving a product. Currently simple; kept as a
    mutable dataclass because price updates are a legitimate
    mutation on the aggregate.
    """

    id: str
    name: str
    price: Money

    def update_price(self, new_price: Money) -> None:
        """Change the product price.

        This does NOT affect any existing orders because orders
        capture a price snapshot at creation time.
        """
        if new_price.amount <= 0:
            raise ValidationError("Product price must be greater than zero")
        self.price = new_price
