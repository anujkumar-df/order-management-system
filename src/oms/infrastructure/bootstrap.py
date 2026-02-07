"""Composition root — wires concrete implementations to domain interfaces.

This is the only place in the codebase that knows about *all* layers.
Every other module depends only on abstractions.
"""

from __future__ import annotations

from pathlib import Path

from oms.infrastructure.persistence.json_order_repository import (
    JsonOrderRepository,
)
from oms.infrastructure.persistence.json_product_repository import (
    JsonProductRepository,
)

# Resolve data directory relative to the project root.
# When installed in editable mode the project root is the repo root.
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def product_repository() -> JsonProductRepository:
    return JsonProductRepository(_DATA_DIR / "products.json")


def order_repository() -> JsonOrderRepository:
    return JsonOrderRepository(_DATA_DIR / "orders.json")
