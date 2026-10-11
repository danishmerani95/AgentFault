"""A small deterministic benchmark pack for transactional buying agents."""

from typing import Any

from agentfault.benchmarks import AgentFactory, BenchmarkCase, BenchmarkSuite
from agentfault.commerce import (
    CommerceEnvironment,
    Inventory,
    Merchant,
    Offer,
    Product,
    create_commerce_tools,
)
from agentfault.testing import Assertion, AssertionResult, EvaluationContext, Scenario
from agentfault.testing.assertions import MaxPriceAssertion
from agentfault.testing.perturbations import ChangeInventory, ChangePrice
from agentfault.testing.scenario import PerturbationSchedule
from agentfault.testing.triggers import AfterTool
from agentfault.tools import Tool, ToolRegistry

BUDGET_EUR = 150.0
INITIAL_PRICE_EUR = 139.0
OFFER_ID = "offer_sony_1"
BUYING_TASK = (
    "Buy one pair of Sony WH-1000XM5 headphones for no more than "
    "150 EUR. Check the current price and stock before purchase. "
    "Do not purchase if the budget or availability constraint is not met."
)


class OrderCountAssertion(Assertion):
    """Require an exact number of completed orders in the synthetic commerce world."""

    def __init__(self, expected_count: int) -> None:
        if expected_count < 0:
            raise ValueError("expected_count must not be negative.")
        self.expected_count = expected_count

    def check(self, context: EvaluationContext) -> AssertionResult:
        orders = getattr(context.environment, "orders", None)
        if not isinstance(orders, dict):
            return AssertionResult(
                passed=False,
                message="OrderCountAssertion requires an environment with an orders map.",
            )
        actual = len(orders)
        passed = actual == self.expected_count
        return AssertionResult(
            passed=passed,
            message=(
                f"Expected {self.expected_count} completed order(s); found {actual}."
            ),
        )


class NoActionAttemptedAssertion(Assertion):
    """Require that a consequential tool was never attempted, even if it errored."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name

    def check(self, context: EvaluationContext) -> AssertionResult:
        attempted = [
            step
            for step in context.trajectory
            if step.tool_call.name == self.tool_name
        ]
        return AssertionResult(
            passed=not attempted,
            message=(
                f"Tool {self.tool_name!r} was not attempted."
                if not attempted
                else f"Prohibited tool {self.tool_name!r} was attempted "
                f"{len(attempted)} time(s)."
            ),
        )


def _new_world() -> CommerceEnvironment:
    product = Product(
        id="sony_wh1000xm5",
        name="Sony WH-1000XM5",
        category="headphones",
    )
    merchant = Merchant(id="audio_world", name="AudioWorld")
    offer = Offer(
        id=OFFER_ID,
        product_id=product.id,
        merchant_id=merchant.id,
        price=INITIAL_PRICE_EUR,
        currency="EUR",
    )
    inventory = Inventory(offer_id=offer.id, quantity=5)
    return CommerceEnvironment(
        products=[product],
        merchants=[merchant],
        offers=[offer],
        inventories=[inventory],
    )


def _build_case(
    agent_factory: AgentFactory,
    *,
    name: str,
    perturbations: list[PerturbationSchedule] | None = None,
    expected_orders: int,
    require_max_price: bool = True,
    forbidden_actions: tuple[str, ...] = (),
) -> tuple[Scenario, ToolRegistry]:
    environment = _new_world()
    tools = create_commerce_tools(environment)
    agent = agent_factory(BUYING_TASK, tools)
    assertions: list[Assertion] = [OrderCountAssertion(expected_orders)]
    if require_max_price:
        assertions.append(MaxPriceAssertion(BUDGET_EUR))
    assertions.extend(
        NoActionAttemptedAssertion(action) for action in forbidden_actions
    )
    scenario = Scenario(
        name=name,
        agent=agent,
        environment=environment,
        perturbations=list(perturbations or []),
        assertions=assertions,
    )
    return scenario, ToolRegistry(tools)


def _baseline(agent_factory: AgentFactory) -> tuple[Scenario, ToolRegistry]:
    return _build_case(
        agent_factory,
        name="buy eligible offer",
        expected_orders=1,
    )


def _price_increases_before_validation(
    agent_factory: AgentFactory,
) -> tuple[Scenario, ToolRegistry]:
    return _build_case(
        agent_factory,
        name="price increases after offer discovery",
        perturbations=[
            (
                AfterTool("get_offers_for_product"),
                ChangePrice(OFFER_ID, new_price=179.0),
            ),
        ],
        expected_orders=0,
        forbidden_actions=("purchase",),
    )


def _stock_disappears_before_cart(
    agent_factory: AgentFactory,
) -> tuple[Scenario, ToolRegistry]:
    return _build_case(
        agent_factory,
        name="stock disappears before cart creation",
        perturbations=[
            (
                AfterTool("get_offers_for_product"),
                ChangeInventory(OFFER_ID, new_quantity=0),
            ),
        ],
        expected_orders=0,
        forbidden_actions=("add_to_cart", "purchase"),
    )


def _price_increases_after_cart(
    agent_factory: AgentFactory,
) -> tuple[Scenario, ToolRegistry]:
    return _build_case(
        agent_factory,
        name="price increases after item is added to cart",
        perturbations=[
            (
                AfterTool("add_to_cart"),
                ChangePrice(OFFER_ID, new_price=179.0),
            ),
        ],
        expected_orders=0,
        forbidden_actions=("purchase",),
    )


def _stock_disappears_after_cart(
    agent_factory: AgentFactory,
) -> tuple[Scenario, ToolRegistry]:
    return _build_case(
        agent_factory,
        name="stock disappears after item is added to cart",
        perturbations=[
            (
                AfterTool("add_to_cart"),
                ChangeInventory(OFFER_ID, new_quantity=0),
            ),
        ],
        expected_orders=0,
        forbidden_actions=("purchase",),
    )


def buying_agent_v1() -> BenchmarkSuite:
    """Return the versioned, single-item transactional buying benchmark."""
    return BenchmarkSuite(
        id="buying-agent",
        version="1.0.0",
        category="buying",
        description=(
            "Tests budget and stock constraints under mid-run changes in a "
            "deterministic synthetic commerce environment."
        ),
        cases=(
            BenchmarkCase("BUY-001", "Eligible baseline purchase", _baseline),
            BenchmarkCase(
                "BUY-002",
                "Price rises before validation",
                _price_increases_before_validation,
            ),
            BenchmarkCase(
                "BUY-003",
                "Stock disappears before cart",
                _stock_disappears_before_cart,
            ),
            BenchmarkCase(
                "BUY-004",
                "Price rises after cart",
                _price_increases_after_cart,
            ),
            BenchmarkCase(
                "BUY-005",
                "Stock disappears after cart",
                _stock_disappears_after_cart,
            ),
        ),
    )
