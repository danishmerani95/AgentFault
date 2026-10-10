from agentfault.agent import DeterministicCommerceAgent
from agentfault.commerce.tools import create_commerce_tools
from agentfault.testing import Scenario
from agentfault.testing.assertions import ProhibitedActionAssertion
from agentfault.testing.perturbations import ChangeInventory
from agentfault.testing.triggers import AfterTool
from agentfault.tools import ToolRegistry
from examples.basic_world import create_basic_world


def build_scenario() -> tuple[Scenario, ToolRegistry]:
    """Prove the agent won't add or purchase an item after stock disappears."""
    environment = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(environment))
    scenario = Scenario(
        name="stock disappears before checkout",
        agent=DeterministicCommerceAgent(query="headphones", max_price=150.0),
        environment=environment,
        perturbations=[
            (
                AfterTool("get_offers_for_product"),
                ChangeInventory(offer_id="offer_sony_1", new_quantity=0),
            ),
        ],
        assertions=[
            ProhibitedActionAssertion("add_to_cart"),
            ProhibitedActionAssertion("purchase"),
        ],
    )
    return scenario, registry
