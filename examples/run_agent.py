from cartspec.commerce_tools import create_commerce_tools
from cartspec.deterministic_agent import DeterministicCommerceAgent
from cartspec.runner import AgentRunner
from cartspec.tool import ToolRegistry
from examples.basic_world import create_basic_world


def main() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    runner = AgentRunner(
        agent=agent,
        tool_registry=registry,
    )

    result = runner.run()

    print("\n=== CartSpec Run ===")

    for index, step in enumerate(runner.trajectory, start=1):
        print(f"\n{index}. {step.tool_call.name}")
        print(f" Arguments: {step.tool_call.arguments}")
        print(f" Result: {step.observation}")

    print(f"Orders: {result}")

    print("\n=== Final Environment ===")
    print(f"Inventory: {world.inventories}")
    print(f"Orders: {world.orders}")
    print(f"Carts: {world.carts}")


if __name__ == "__main__":
    main()
