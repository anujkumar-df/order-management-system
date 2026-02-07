"""Unit tests for the InventoryItem aggregate."""

import pytest

from oms.domain.exceptions import ValidationError
from oms.domain.model.inventory import InventoryItem


class TestInventoryItemReserve:

    def test_reserve_reduces_available(self):
        inv = InventoryItem(product_id="1", product_name="Widget", total_quantity=100)
        inv.reserve(30)
        assert inv.available_quantity == 70
        assert inv.reserved_quantity == 30

    def test_reserve_all_available(self):
        inv = InventoryItem(product_id="1", product_name="Widget", total_quantity=10)
        inv.reserve(10)
        assert inv.available_quantity == 0
        assert inv.reserved_quantity == 10

    def test_reserve_more_than_available_rejected(self):
        inv = InventoryItem(product_id="1", product_name="Widget", total_quantity=10)
        with pytest.raises(ValidationError, match="Insufficient inventory"):
            inv.reserve(11)

    def test_reserve_with_existing_reservations(self):
        inv = InventoryItem(
            product_id="1", product_name="Widget",
            total_quantity=100, reserved_quantity=60,
        )
        inv.reserve(30)
        assert inv.available_quantity == 10
        assert inv.reserved_quantity == 90

    def test_reserve_zero_rejected(self):
        inv = InventoryItem(product_id="1", product_name="Widget", total_quantity=100)
        with pytest.raises(ValidationError, match="must be positive"):
            inv.reserve(0)

    def test_reserve_negative_rejected(self):
        inv = InventoryItem(product_id="1", product_name="Widget", total_quantity=100)
        with pytest.raises(ValidationError, match="must be positive"):
            inv.reserve(-5)


class TestInventoryItemRelease:

    def test_release_increases_available(self):
        inv = InventoryItem(
            product_id="1", product_name="Widget",
            total_quantity=100, reserved_quantity=30,
        )
        inv.release(10)
        assert inv.available_quantity == 80
        assert inv.reserved_quantity == 20

    def test_release_all_reserved(self):
        inv = InventoryItem(
            product_id="1", product_name="Widget",
            total_quantity=100, reserved_quantity=30,
        )
        inv.release(30)
        assert inv.available_quantity == 100
        assert inv.reserved_quantity == 0

    def test_release_more_than_reserved_rejected(self):
        inv = InventoryItem(
            product_id="1", product_name="Widget",
            total_quantity=100, reserved_quantity=10,
        )
        with pytest.raises(ValidationError, match="Cannot release"):
            inv.release(11)

    def test_release_zero_rejected(self):
        inv = InventoryItem(
            product_id="1", product_name="Widget",
            total_quantity=100, reserved_quantity=10,
        )
        with pytest.raises(ValidationError, match="must be positive"):
            inv.release(0)


class TestInventoryItemAvailable:

    def test_available_is_total_minus_reserved(self):
        inv = InventoryItem(
            product_id="1", product_name="Widget",
            total_quantity=100, reserved_quantity=25,
        )
        assert inv.available_quantity == 75

    def test_available_when_nothing_reserved(self):
        inv = InventoryItem(product_id="1", product_name="Widget", total_quantity=50)
        assert inv.available_quantity == 50
