from typing import Any

from cartspec.testing.assertion import Assertion, AssertionResult


class MaxPriceAssertion(Assertion):
    def __init__(self, max_price: float) -> None:
        self.max_price = max_price

    def check(
        self,
        result: Any,
        trajectory: Any,
    ) -> AssertionResult:
        if not result:
            return AssertionResult(
                passed=False,
                message="No purchase was completed.",
            )

        total_price = sum(order.total_price for order in result)

        if total_price <= self.max_price:
            return AssertionResult(
                passed=True,
                message=(
                    f"Purchase total €{total_price:.2f} "
                    f"is within maximum €{self.max_price:.2f}."
                ),
            )

        return AssertionResult(
            passed=False,
            message=(
                f"Purchase total €{total_price:.2f} "
                f"exceeded maximum €{self.max_price:.2f}."
            ),
        )
