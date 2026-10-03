from typing import Any, cast

from cartspec.commerce.environment import CommerceEnvironment
from cartspec.testing.perturbations.base import Perturbation


class ChangePrice(Perturbation):
    def __init__(self, offer_id: str, new_price: float) -> None:
        self.offer_id = offer_id
        self.new_price = new_price

    def apply(self, environment: Any) -> None:
        commerce_environment = cast(CommerceEnvironment, environment)
        commerce_environment.offers[self.offer_id].price = self.new_price
