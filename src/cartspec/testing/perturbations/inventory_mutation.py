from cartspec.commerce.environment import CommerceEnvironment
from cartspec.testing.perturbations.base import Perturbation


class InventoryMutation(Perturbation):
    def __init__(self, offer_id: str, new_quantity: int):
        self.offer_id = offer_id
        self.new_quantity = new_quantity

    def apply(self, environment: CommerceEnvironment) -> None:
        environment.inventories[self.offer_id].quantity = self.new_quantity
