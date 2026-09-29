import pytest
from src.modules.order.discounts import DiscountCode, DiscountRegistry, DiscountType


def test_percentage_discount_calculation():
    discount = DiscountCode(code="SAVE20", discount_type=DiscountType.PERCENTAGE, value=20.0)
    original_price = 100.0

    assert discount.calculate_discount(original_price) == 20.0
    assert discount.calculate_final_price(original_price) == 80.0


def test_fixed_amount_discount_calculation():
    discount = DiscountCode(code="SAVE15", discount_type=DiscountType.FIXED_AMOUNT, value=15.0)
    original_price = 50.0

    assert discount.calculate_discount(original_price) == 15.0
    assert discount.calculate_final_price(original_price) == 35.0


def test_fixed_amount_cannot_exceed_total():
    discount = DiscountCode(code="SAVE100", discount_type=DiscountType.FIXED_AMOUNT, value=100.0)
    original_price = 45.0

    assert discount.calculate_discount(original_price) == 45.0
    assert discount.calculate_final_price(original_price) == 0.0


def test_discount_max_uses_quota():
    discount = DiscountCode(code="LIMITED", discount_type=DiscountType.PERCENTAGE, value=10.0, max_uses=2)

    assert discount.is_valid() is True
    discount.redeem()
    assert discount.is_valid() is True
    discount.redeem()
    assert discount.is_valid() is False

    with pytest.raises(ValueError, match="is no longer valid"):
        discount.redeem()


def test_discount_registry_lookup():
    registry = DiscountRegistry()
    assert registry.get_coupon("earlybird20") is not None
    assert registry.get_coupon("INVALID_CODE") is None
