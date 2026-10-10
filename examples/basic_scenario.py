from agentfault.agent import DeterministicCommerceAgent
from agentfault.commerce.tools import create_commerce_tools
from agentfault.testing import Scenario
from agentfault.testing.assertions import MaxPriceAssertion
from agentfault.tools import ToolRegistry
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
