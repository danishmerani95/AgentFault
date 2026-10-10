from typing import Any, cast

from agentfault.commerce.environment import CommerceEnvironment
from agentfault.testing.perturbations.base import Perturbation


class ChangeInventory(Perturbation):
    def __init__(self, offer_id: str, new_quantity: int) -> None:
        self.offer_id = offer_id
        self.new_quantity = new_quantity

    def apply(self, environment: Any) -> None:
        commerce_environment = cast(CommerceEnvironment, environment)
        commerce_environment.inventories[self.offer_id].quantity = self.new_quantity
