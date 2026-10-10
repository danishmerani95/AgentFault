from agentfault.commerce import Order
from agentfault.testing import EvaluationContext
from agentfault.testing.assertions.budget import MaxPriceAssertion
from examples.basic_world import create_basic_world


def test_max_price_passes() -> None:
    assertion = MaxPriceAssertion(max_price=150.0)

    world = create_basic_world()
    world.orders["order_1"] = Order(
        id="order_1",
        offer_id="offer_1",
        quantity=1,
        unit_price=139.0,
        currency="EUR",
        total_price=139.0,
        status="completed",
    )

    assertion_result = assertion.check(EvaluationContext(None, [], None, world))

    assert assertion_result.passed is True


def test_max_price_fails() -> None:
    assertion = MaxPriceAssertion(max_price=150.0)

    world = create_basic_world()
    world.orders["order_1"] = Order(
        id="order_1",
        offer_id="offer_1",
        quantity=1,
        unit_price=179.0,
        currency="EUR",
        total_price=179.0,
        status="completed",
    )

    assertion_result = assertion.check(EvaluationContext(None, [], None, world))

    assert assertion_result.passed is False
