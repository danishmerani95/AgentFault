# from dotenv import load_dotenv

# from cartspec.commerce.tools import create_commerce_tools
# from cartspec.integrations.openai import OpenAICommerceAgent, to_openai_tools
# from cartspec.testing.assertions.budget import MaxPriceAssertion
# from cartspec.testing.scenario import Scenario
# from cartspec.testing.test_runner import TestRunner
# from cartspec.tools.tool import ToolRegistry
# from examples.basic_world import create_basic_world

# load_dotenv()


# def test_openai_agent_passes_budget_constraint() -> None:
#     world = create_basic_world()

#     tools = create_commerce_tools(world)
#     registry = ToolRegistry(tools)

#     openai_tools = to_openai_tools(tools)

#     agent = OpenAICommerceAgent(
#         query="headphones",
#         max_price=150.0,
#         tools=openai_tools,
#         model="gpt-4o-mini",
#     )

#     scenario = Scenario(
#         name="budget_constraint",
#         assertions=[
#             MaxPriceAssertion(max_price=150.0),
#         ],
#     )

#     runner = TestRunner(agent=agent, tool_registry=registry, environment=world)

#     result = runner.run(scenario)

#     assert result.passed is True
#     assert len(result.assertions) == 1
#     assert result.assertions[0].passed is True
