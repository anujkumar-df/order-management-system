"""JSON-file-backed implementation of OrderRepository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from oms.domain.model.order import Order, OrderLineItem, OrderStatus
from oms.domain.model.value_objects import Money, Quantity
from oms.domain.repository.order_repository import OrderRepository


class JsonOrderRepository(OrderRepository):

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._ensure_file()

    # --- OrderRepository interface --------------------------------------------

    def next_id(self) -> int:
        orders = self._load_raw()
        if not orders:
            return 1
        return max(o["id"] for o in orders) + 1

    def get_by_id(self, order_id: int) -> Order | None:
        for raw in self._load_raw():
            if raw["id"] == order_id:
                return self._to_domain(raw)
        return None

    def save(self, order: Order) -> None:
        orders = self._load_raw()

        if order.id is None:
            order.id = self.next_id()

        # Upsert: replace if exists, otherwise append
        replaced = False
        for i, raw in enumerate(orders):
            if raw["id"] == order.id:
                orders[i] = self._to_raw(order)
                replaced = True
                break
        if not replaced:
            orders.append(self._to_raw(order))

        self._persist_raw(orders)

    # --- Serialization --------------------------------------------------------

    @staticmethod
    def _to_raw(order: Order) -> dict:
        return {
            "id": order.id,
            "customer_name": order.customer_name,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity.value,
                    "unit_price": str(item.unit_price.amount),
                    "currency": item.unit_price.currency,
                }
                for item in order.items
            ],
        }

    @staticmethod
    def _to_domain(raw: dict) -> Order:
        items = [
            OrderLineItem(
                product_id=i["product_id"],
                product_name=i["product_name"],
                quantity=Quantity(i["quantity"]),
                unit_price=Money(Decimal(i["unit_price"]), i.get("currency", "USD")),
            )
            for i in raw["items"]
        ]
        return Order(
            id=raw["id"],
            customer_name=raw["customer_name"],
            items=items,
            status=OrderStatus(raw["status"]),
            created_at=datetime.fromisoformat(raw["created_at"]),
        )

    # --- File helpers ---------------------------------------------------------

    def _load_raw(self) -> list[dict]:
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _persist_raw(self, orders: list[dict]) -> None:
        self._file_path.write_text(
            json.dumps(orders, indent=2) + "\n", encoding="utf-8"
        )

    def _ensure_file(self) -> None:
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text("[]", encoding="utf-8")
