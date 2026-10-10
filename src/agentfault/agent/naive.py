from typing import Any

from agentfault.agent.base import Agent
from agentfault.tools.tool import ToolCall


class NaiveCommerceAgent(Agent):
    def __init__(self, query: str) -> None:
        self.query = query
        self.step = 0
        self.offer_id: str | None = None
        self.cart_id: str | None = None

    def next_action(self, observation: Any) -> ToolCall | None:
        if self.step == 0:
            self.step += 1
            return ToolCall(
                name="search_products",
                arguments={"query": self.query},
            )

        if self.step == 1:
            product = observation[0]
            self.step += 1
            return ToolCall(
                name="get_offers_for_product",
                arguments={"product_id": product.id},
            )

        if self.step == 2:
            offer = observation[0]
            self.offer_id = offer.id
            self.step += 1
            return ToolCall(name="create_cart", arguments={})

        if self.step == 3:
            self.cart_id = observation.id
            self.step += 1
            return ToolCall(
                name="add_to_cart",
                arguments={
                    "cart_id": self.cart_id,
                    "offer_id": self.offer_id,
                    "quantity": 1,
                },
            )

        if self.step == 4:
            self.step += 1
            return ToolCall(
                name="purchase",
                arguments={"cart_id": self.cart_id},
            )

        return None
