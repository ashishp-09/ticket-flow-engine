from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


@dataclass
class DiscountCode:
    code: str
    discount_type: DiscountType
    value: float
    max_uses: Optional[int] = None
    used_count: int = 0
    active: bool = True

    def calculate_discount(self, original_price: float) -> float:
        if not self.is_valid():
            return 0.0

        if self.discount_type == DiscountType.PERCENTAGE:
            discount = original_price * (self.value / 100.0)
        else:
            discount = self.value

        return min(round(discount, 2), original_price)

    def calculate_final_price(self, original_price: float) -> float:
        discount = self.calculate_discount(original_price)
        return max(0.0, round(original_price - discount, 2))

    def is_valid(self) -> bool:
        if not self.active:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def redeem(self) -> None:
        if not self.is_valid():
            raise ValueError(f"Discount code '{self.code}' is no longer valid or has reached max uses.")
        self.used_count += 1


class DiscountRegistry:
    def __init__(self) -> None:
        self._discounts: dict[str, DiscountCode] = {
            "EARLYBIRD20": DiscountCode(code="EARLYBIRD20", discount_type=DiscountType.PERCENTAGE, value=20.0, max_uses=500),
            "VIP10OFF": DiscountCode(code="VIP10OFF", discount_type=DiscountType.FIXED_AMOUNT, value=10.0, max_uses=100),
            "FLASH50": DiscountCode(code="FLASH50", discount_type=DiscountType.PERCENTAGE, value=50.0, max_uses=50),
        }

    def get_coupon(self, code: str) -> Optional[DiscountCode]:
        return self._discounts.get(code.upper().strip())


discount_registry = DiscountRegistry()
