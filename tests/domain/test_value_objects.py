"""Unit tests for domain value objects."""

from decimal import Decimal

import pytest

from oms.domain.exceptions import ValidationError
from oms.domain.model.value_objects import Money, Quantity


# ── Money ────────────────────────────────────────────────────────────────────


class TestMoney:

    def test_creation(self):
        m = Money(Decimal("10.50"))
        assert m.amount == Decimal("10.50")
        assert m.currency == "USD"

    def test_of_factory_from_string(self):
        m = Money.of("25.99")
        assert m.amount == Decimal("25.99")

    def test_of_factory_from_int(self):
        m = Money.of(10)
        assert m.amount == Decimal("10")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError, match="cannot be negative"):
            Money(Decimal("-1"))

    def test_addition(self):
        result = Money.of("10") + Money.of("5.50")
        assert result == Money.of("15.50")

    def test_subtraction(self):
        result = Money.of("10") - Money.of("3")
        assert result == Money.of("7")

    def test_subtraction_going_negative_rejected(self):
        with pytest.raises(ValidationError, match="negative amount"):
            Money.of("5") - Money.of("10")

    def test_multiplication_by_int(self):
        result = Money.of("7.50") * 3
        assert result == Money.of("22.50")

    def test_currency_mismatch_rejected(self):
        with pytest.raises(ValidationError, match="Cannot combine"):
            Money(Decimal("10"), "USD") + Money(Decimal("5"), "EUR")

    def test_str_formatting(self):
        assert str(Money.of("15")) == "$15.00"
        assert str(Money.of("9.5")) == "$9.50"

    def test_comparison_operators(self):
        assert Money.of("5") < Money.of("10")
        assert Money.of("10") > Money.of("5")
        assert Money.of("10") >= Money.of("10")
        assert Money.of("10") <= Money.of("10")


# ── Quantity ─────────────────────────────────────────────────────────────────


class TestQuantity:

    def test_valid_quantity(self):
        q = Quantity(5)
        assert q.value == 5

    def test_zero_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            Quantity(0)

    def test_negative_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            Quantity(-3)

    def test_str(self):
        assert str(Quantity(7)) == "7"
