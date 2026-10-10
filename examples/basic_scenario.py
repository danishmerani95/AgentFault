from cartspec.agent import DeterministicCommerceAgent
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing import Scenario
from cartspec.testing.assertions import MaxPriceAssertion
from cartspec.tools import ToolRegistry
from examples.basic_world import create_basic_world


def build_scenario() -> tuple[Scenario, ToolRegistry]:
    """Factory used by the CLI and pytest integration examples."""
    environment = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(environment))
    scenario = Scenario(
        name="headphones within budget",
        agent=DeterministicCommerceAgent(
            query="headphones",
            max_price=150.0,
        ),
        environment=environment,
        assertions=[MaxPriceAssertion(max_price=150.0)],
    )
    return scenario, registry
