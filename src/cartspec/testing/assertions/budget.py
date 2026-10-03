from cartspec.commerce import CommerceEnvironment
from cartspec.testing.assertion import Assertion, AssertionResult, EvaluationContext


class MaxPriceAssertion(Assertion):
    def __init__(self, max_price: float) -> None:
        self.max_price = max_price

    def check(self, context: EvaluationContext) -> AssertionResult:
        environment = context.environment
        if not isinstance(environment, CommerceEnvironment):
            return AssertionResult(
                passed=False,
                message="MaxPriceAssertion requires a CommerceEnvironment.",
            )

        over_budget_orders = [
            order
            for order in environment.orders.values()
            if order.total_price > self.max_price
        ]

        if not over_budget_orders:
            return AssertionResult(
                passed=True,
                message=(
                    f"All completed purchases are within maximum "
                    f"€{self.max_price:.2f}."
                ),
            )

        highest_price = max(order.total_price for order in over_budget_orders)
        return AssertionResult(
            passed=False,
            message=(
                f"Completed purchase €{highest_price:.2f} "
                f"exceeded maximum €{self.max_price:.2f}."
            ),
        )
