from typing import Any

from agentfault.agent import Agent
from agentfault.tools.tool import ToolCall


class DeterministicCommerceAgent(Agent):
    """Reference buyer that rechecks offer price and stock before purchase."""

    def __init__(self, query: str, max_price: float) -> None:
        self.query = query
        self.max_price = max_price
        self.step = 0
        self.offer_id: str | None = None
        self.cart_id: str | None = None

    def next_action(self, observation: Any) -> ToolCall | None:
        if self.step == 0:
            self.step = 1
            return ToolCall("search_products", {"query": self.query})

        if self.step == 1:
            self.step = 2
            if not observation:
                return None
            return ToolCall(
                "get_offers_for_product",
                {"product_id": observation[0].id},
            )

        if self.step == 2:
            self.step = 3
            if not observation:
                return None
            self.offer_id = observation[0].id
            return ToolCall("get_offer", {"offer_id": self.offer_id})

        if self.step == 3:
            self.step = 4
            if observation.price > self.max_price:
                return None
            return ToolCall("check_inventory", {"offer_id": self.offer_id})

        if self.step == 4:
            self.step = 5
            if observation.quantity < 1:
                return None
            return ToolCall("create_cart", {})

        if self.step == 5:
            self.step = 6
            self.cart_id = observation.id
            return ToolCall(
                "add_to_cart",
                {
                    "cart_id": self.cart_id,
                    "offer_id": self.offer_id,
                    "quantity": 1,
                },
            )

        # Cart creation is not the last safety boundary: offer and stock may
        # have changed after the item was added.
        if self.step == 6:
            self.step = 7
            return ToolCall("get_offer", {"offer_id": self.offer_id})

        if self.step == 7:
            self.step = 8
            if observation.price > self.max_price:
                return None
            return ToolCall("check_inventory", {"offer_id": self.offer_id})

        if self.step == 8:
            self.step = 9
            if observation.quantity < 1:
                return None
            return ToolCall("purchase", {"cart_id": self.cart_id})

        return None
