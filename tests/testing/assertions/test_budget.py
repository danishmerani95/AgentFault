from cartspec.commerce import Order
from cartspec.testing.assertions.budget import MaxPriceAssertion


def test_max_price_passes() -> None:
    assertion = MaxPriceAssertion(max_price=150.0)

    result = [
        Order(
            id="order_1",
            offer_id="offer_1",
            quantity=1,
            unit_price=139.0,
            currency="EUR",
            total_price=139.0,
            status="completed",
        )
    ]

    assertion_result = assertion.check(result, [])

    assert assertion_result.passed is True


def test_max_price_fails() -> None:
    assertion = MaxPriceAssertion(max_price=150.0)

    result = [
        Order(
            id="order_1",
            offer_id="offer_1",
            quantity=1,
            unit_price=179.0,
            currency="EUR",
            total_price=179.0,
            status="completed",
        )
    ]

    assertion_result = assertion.check(result, [])

    assert assertion_result.passed is False
