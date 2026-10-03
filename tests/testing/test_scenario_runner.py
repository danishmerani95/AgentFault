from cartspec.agent import DeterministicCommerceAgent, NaiveCommerceAgent
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing import Assertion, AssertionResult, EvaluationContext
from cartspec.testing.assertions import MaxPriceAssertion, ProhibitedActionAssertion
from cartspec.testing.perturbations import ChangeInventory, ChangePrice, FailTool
from cartspec.testing.scenario import Scenario
from cartspec.testing.scenario_runner import ScenarioRunner
from cartspec.testing.triggers import AfterTool, BeforeTool
from cartspec.tools import ToolCall, ToolRegistry
from examples.basic_world import create_basic_world


def test_budget_constraint_passes() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    scenario = Scenario(
        name="budget_constraint",
        agent=agent,
        environment=world,
        assertions=[
            MaxPriceAssertion(max_price=150.0),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)

    result = runner.run(scenario)

    assert result.passed is True
    assert len(result.assertions) == 1
    assert result.assertions[0].passed is True


def test_agent_revalidates_price_after_price_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    scenario = Scenario(
        name="budget_constraint",
        agent=agent,
        environment=world,
        assertions=[MaxPriceAssertion(max_price=150.0)],
        perturbations=[
            (
                AfterTool(tool_name="get_offers_for_product"),
                ChangePrice(
                    offer_id="offer_sony_1",
                    new_price=179.0,
                ),
            ),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)
    result = runner.run(scenario)

    assert result.passed is True
    assert result.assertions[0].passed is True
    assert world.orders == {}
    assert world.offers["offer_sony_1"].price == 179.0


def test_naive_agent_violates_budget_after_price_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = NaiveCommerceAgent(query="headphones")

    scenario = Scenario(
        name="budget_constraint",
        agent=agent,
        environment=world,
        assertions=[
            MaxPriceAssertion(max_price=150.0),
        ],
        perturbations=[
            (
                AfterTool(tool_name="get_offers_for_product"),
                ChangePrice(
                    offer_id="offer_sony_1",
                    new_price=179.0,
                ),
            ),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)

    result = runner.run(scenario)
    assert result.passed is False
    assert result.assertions[0].passed is False


def test_different_valid_trajectories_satisfy_the_same_budget_assertion() -> None:
    deterministic_world = create_basic_world()
    deterministic_scenario = Scenario(
        name="deterministic within budget",
        agent=DeterministicCommerceAgent(query="headphones", max_price=150.0),
        environment=deterministic_world,
        assertions=[MaxPriceAssertion(max_price=150.0)],
    )
    deterministic_result = ScenarioRunner(
        ToolRegistry(create_commerce_tools(deterministic_world))
    ).run(deterministic_scenario)

    naive_world = create_basic_world()
    naive_scenario = Scenario(
        name="naive within budget",
        agent=NaiveCommerceAgent(query="headphones"),
        environment=naive_world,
        assertions=[MaxPriceAssertion(max_price=150.0)],
    )
    naive_result = ScenarioRunner(ToolRegistry(create_commerce_tools(naive_world))).run(
        naive_scenario
    )

    assert deterministic_result.passed is True
    assert naive_result.passed is True
    assert len(deterministic_result.trajectory) != len(naive_result.trajectory)


def test_prohibited_action_fails_even_when_purchase_is_within_budget() -> None:
    world = create_basic_world()
    scenario = Scenario(
        name="purchase is prohibited",
        agent=DeterministicCommerceAgent(query="headphones", max_price=150.0),
        environment=world,
        assertions=[
            MaxPriceAssertion(max_price=150.0),
            ProhibitedActionAssertion("purchase"),
        ],
    )

    result = ScenarioRunner(ToolRegistry(create_commerce_tools(world))).run(scenario)

    assert result.passed is False
    assert result.assertions[0].passed is True
    assert result.assertions[1].passed is False


class _ErrorIsVisibleAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        return AssertionResult(
            passed=isinstance(context.error, RuntimeError),
            message="Execution error was visible to the assertion.",
        )


class _FinalObservationAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        return AssertionResult(
            passed=bool(context.final_observation),
            message="Final observation was visible to the assertion.",
        )


def test_assertion_receives_final_observation() -> None:
    world = create_basic_world()
    scenario = Scenario(
        name="final observation is available",
        agent=DeterministicCommerceAgent(query="headphones", max_price=150.0),
        environment=world,
        assertions=[_FinalObservationAssertion()],
    )

    result = ScenarioRunner(ToolRegistry(create_commerce_tools(world))).run(scenario)

    assert result.passed is True
    assert result.assertions[0].passed is True


def test_naive_agent_fails_purchase_after_inventory_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = NaiveCommerceAgent(query="headphones")

    scenario = Scenario(
        name="quantity_constraint",
        agent=agent,
        environment=world,
        assertions=[],
        perturbations=[
            (
                AfterTool(tool_name="get_offers_for_product"),
                ChangeInventory(
                    offer_id="offer_sony_1",
                    new_quantity=0,
                ),
            ),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)

    result = runner.run(scenario)
    assert result.passed is False
    assert result.error is not None
    assert world.inventories["offer_sony_1"].quantity == 0


def test_before_tool_price_change_modifies_selected_tool_observation() -> None:
    world = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(world))
    agent = DeterministicCommerceAgent(query="headphones", max_price=200.0)

    scenario = Scenario(
        name="before price change",
        agent=agent,
        environment=world,
        perturbations=[
            (
                BeforeTool("get_offers_for_product"),
                ChangePrice(offer_id="offer_sony_1", new_price=179.0),
            )
        ],
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.error is None
    assert result.trajectory[1].observation[0].price == 179.0


def test_after_tool_price_change_preserves_produced_observation() -> None:
    world = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(world))
    agent = DeterministicCommerceAgent(query="headphones", max_price=150.0)

    scenario = Scenario(
        name="after price change",
        agent=agent,
        environment=world,
        perturbations=[
            (
                AfterTool("get_offers_for_product"),
                ChangePrice(offer_id="offer_sony_1", new_price=179.0),
            )
        ],
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.error is None
    assert result.trajectory[1].observation[0].price == 139.0
    assert result.trajectory[2].observation.price == 179.0
    assert world.offers["offer_sony_1"].price == 179.0


def test_before_tool_inventory_change_fails_selected_tool_execution() -> None:
    world = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(world))
    agent = NaiveCommerceAgent(query="headphones")

    scenario = Scenario(
        name="before inventory change",
        agent=agent,
        environment=world,
        perturbations=[
            (
                BeforeTool("add_to_cart"),
                ChangeInventory(offer_id="offer_sony_1", new_quantity=0),
            )
        ],
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.error is not None
    assert len(result.trajectory) == 3
    assert result.trajectory[-1].tool_call.name == "create_cart"


class _SingleToolAgent:
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        self.calls = 0

    def next_action(self, observation: object) -> ToolCall | None:
        self.calls += 1
        if self.calls == 1:
            return ToolCall(name=self.tool_name, arguments={})
        return None


def test_fail_tool_injects_error_without_executing_real_tool() -> None:
    world = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(world))
    agent = _SingleToolAgent("create_cart")
    scenario = Scenario(
        name="failed create cart",
        agent=agent,
        environment=world,
        assertions=[_ErrorIsVisibleAssertion()],
        perturbations=[(BeforeTool("create_cart"), FailTool("Injected tool failure."))],
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.passed is False
    assert isinstance(result.error, RuntimeError)
    assert str(result.error) == "Injected tool failure."
    assert result.assertions[0].passed is True
    assert result.trajectory == []
    assert world.carts == {}


def test_multiple_perturbations_apply_after_the_same_tool() -> None:
    world = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(world))
    agent = DeterministicCommerceAgent(query="headphones", max_price=150.0)
    scenario = Scenario(
        name="multiple changes",
        agent=agent,
        environment=world,
        perturbations=[
            (
                AfterTool("get_offers_for_product"),
                ChangePrice(offer_id="offer_sony_1", new_price=179.0),
            ),
            (
                AfterTool("get_offers_for_product"),
                ChangeInventory(offer_id="offer_sony_1", new_quantity=0),
            ),
        ],
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.trajectory[1].observation[0].price == 139.0
    assert world.offers["offer_sony_1"].price == 179.0
    assert world.inventories["offer_sony_1"].quantity == 0
