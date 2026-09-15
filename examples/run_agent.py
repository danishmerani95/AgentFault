from dotenv import load_dotenv

from cartspec.commerce_tools import create_commerce_tools
from cartspec.openai_agent import OpenAICommerceAgent
from cartspec.openai_tools import to_openai_tools
from cartspec.runner import AgentRunner
from cartspec.tool import ToolRegistry
from examples.basic_world import create_basic_world

load_dotenv()


def main() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    openai_tools = to_openai_tools(tools)

    agent = OpenAICommerceAgent(
        query="headphones",
        max_price=150.0,
        tools=openai_tools,
        model="gpt-4o-mini",
    )

    runner = AgentRunner(
        agent=agent,
        tool_registry=registry,
    )

    result = runner.run()

    print("\n=== CartSpec Run ===")

    for index, step in enumerate(runner.trajectory, start=1):
        print(f"\n--- Step {index} ---")

        print("Tool requested by LLM:")
        print(f"  Name: {step.tool_call.name}")
        print(f"  ID: {step.tool_call.id}")
        print(f"  Arguments: {step.tool_call.arguments}")

        print("\nResult returned by CommerceEnvironment:")
        print(f"  {step.observation}")

    print("\n=== Final Result ===")
    print(result)

    print("\n=== Final Environment ===")
    print(f"Inventory: {world.inventories}")
    print(f"Orders: {world.orders}")
    print(f"Carts: {world.carts}")

    # agent.print_conversation()


if __name__ == "__main__":
    main()
