"""Abstract repository for Order aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod

from oms.domain.model.order import Order


class OrderRepository(ABC):

    @abstractmethod
    def next_id(self) -> int:
        """Generate the next unique order ID."""

    @abstractmethod
    def get_by_id(self, order_id: int) -> Order | None:
        """Return an order by its ID, or None if not found."""

    @abstractmethod
    def save(self, order: Order) -> None:
        """Persist a new or updated order."""
