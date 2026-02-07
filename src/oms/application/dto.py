"""Data Transfer Objects — plain containers that cross layer boundaries.

DTOs carry data between the CLI and application layers without
exposing domain internals to the outside world.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderItemSpec:
    """Input: what the customer asked for (product name + quantity)."""

    product_name: str
    quantity: int


@dataclass(frozen=True)
class OrderLineItemDTO:
    """Output: a single line item as displayed to the user."""

    product_name: str
    quantity: int
    unit_price: str  # formatted, e.g. "$15.00"
    line_total: str


@dataclass(frozen=True)
class OrderDTO:
    """Output: a complete order as displayed to the user."""

    id: int
    customer_name: str
    status: str
    items: list[OrderLineItemDTO]
    total: str
    created_at: str
