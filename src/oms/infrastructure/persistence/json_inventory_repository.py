"""JSON-file-backed implementation of InventoryRepository."""

from __future__ import annotations

import json
from pathlib import Path

from oms.domain.model.inventory import InventoryItem
from oms.domain.repository.inventory_repository import InventoryRepository


class JsonInventoryRepository(InventoryRepository):

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._ensure_file()

    # --- InventoryRepository interface ----------------------------------------

    def get_by_product_id(self, product_id: str) -> InventoryItem | None:
        for raw in self._load_raw():
            if raw["product_id"] == product_id:
                return self._to_domain(raw)
        return None

    def list_all(self) -> list[InventoryItem]:
        return [self._to_domain(raw) for raw in self._load_raw()]

    def save(self, item: InventoryItem) -> None:
        records = self._load_raw()
        replaced = False
        for i, raw in enumerate(records):
            if raw["product_id"] == item.product_id:
                records[i] = self._to_raw(item)
                replaced = True
                break
        if not replaced:
            records.append(self._to_raw(item))
        self._persist_raw(records)

    # --- Serialization --------------------------------------------------------

    @staticmethod
    def _to_raw(item: InventoryItem) -> dict:
        return {
            "product_id": item.product_id,
            "product_name": item.product_name,
            "total_quantity": item.total_quantity,
            "reserved_quantity": item.reserved_quantity,
        }

    @staticmethod
    def _to_domain(raw: dict) -> InventoryItem:
        return InventoryItem(
            product_id=raw["product_id"],
            product_name=raw["product_name"],
            total_quantity=raw["total_quantity"],
            reserved_quantity=raw.get("reserved_quantity", 0),
        )

    # --- File helpers ---------------------------------------------------------

    def _load_raw(self) -> list[dict]:
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _persist_raw(self, records: list[dict]) -> None:
        self._file_path.write_text(
            json.dumps(records, indent=2) + "\n", encoding="utf-8"
        )

    def _ensure_file(self) -> None:
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text("[]", encoding="utf-8")
