from cartspec.agent import Agent
from cartspec.tool import ToolCall


class DeterministicCommerceAgent(Agent):
    def __init__(
        self,
        query: str,
        max_price: float,
    ) -> None:
        self.query = query
        self.max_price = max_price

        self.step = 0
        self.offer_id: str | None = None
        self.cart_id: str | None = None

    def next_action(self, observation: object) -> ToolCall | None:
        if self.step == 0:
            self.step += 1

            return ToolCall(
                name="search_products",
                arguments={"query": self.query},
            )

        if self.step == 1:
            products = observation

            if not products:
                return None

            self.step += 1

            return ToolCall(
                name="get_offer",
                arguments={"offer_id": "offer_sony_1"},
            )

        if self.step == 2:
            offer = observation
            self.offer_id = offer.id

            if offer.price > self.max_price:
                return None

            self.step += 1

            return ToolCall(
                name="check_inventory",
                arguments={"offer_id": self.offer_id},
            )

        if self.step == 3:
            inventory = observation

            if inventory.quantity < 1:
                return None

            self.step += 1

            return ToolCall(
                name="create_cart",
                arguments={},
            )

        if self.step == 4:
            cart = observation
            self.cart_id = cart.id

            self.step += 1

            return ToolCall(
                name="add_to_cart",
                arguments={
                    "cart_id": self.cart_id,
                    "offer_id": self.offer_id,
                    "quantity": 1,
                },
            )

        if self.step == 5:
            self.step += 1

            return ToolCall(
                name="purchase",
                arguments={"cart_id": self.cart_id},
            )

        return None
