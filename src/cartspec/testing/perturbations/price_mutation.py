from cartspec.commerce.environment import CommerceEnvironment
from cartspec.testing.perturbations.base import Perturbation


class PriceMutation(Perturbation):
    def __init__(self, offer_id: str, new_price: float):
        self.offer_id = offer_id
        self.new_price = new_price

    def apply(self, environment: CommerceEnvironment) -> None:
        environment.offers[self.offer_id].price = self.new_price
