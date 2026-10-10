from agentfault.commerce import CommerceEnvironment
from agentfault.tools.tool import Tool


def create_commerce_tools(
    environment: CommerceEnvironment,
) -> list[Tool]:
    return [
        Tool(
            name="search_products",
            description="Search for products by name or category.",
            function=environment.search_products,
        ),
        Tool(
            name="get_offers_for_product",
            description="Get available offers for a product.",
            function=environment.get_offers_for_product,
        ),
        Tool(
            name="get_offer",
            description="Get the details and current price of a product offer.",
            function=environment.get_offer,
        ),
        Tool(
            name="check_inventory",
            description="Check the current inventory for a product offer.",
            function=environment.check_inventory,
        ),
        Tool(
            name="create_cart",
            description="Create a new shopping cart.",
            function=environment.create_cart,
        ),
        Tool(
            name="add_to_cart",
            description="Add an offer to an existing shopping cart.",
            function=environment.add_to_cart,
        ),
        Tool(
            name="purchase",
            description="Purchase all items currently in the shopping cart.",
            function=environment.purchase,
        ),
    ]
