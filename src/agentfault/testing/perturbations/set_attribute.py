from copy import deepcopy
from typing import Any

from agentfault.testing.perturbations.base import Perturbation


class SetAttribute(Perturbation):
    """Set one field on an arbitrary environment object or dictionary.

    This is a general alternative to writing a one-off Perturbation subclass for
    simple scenarios. For nested or computed changes, define a custom class.
    """

    def __init__(self, attribute: str, value: Any) -> None:
        if not attribute.strip():
            raise ValueError("attribute must not be empty.")
        self.attribute = attribute
        self.value = value

    def apply(self, environment: Any) -> None:
        value = deepcopy(self.value)
        if isinstance(environment, dict):
            environment[self.attribute] = value
        else:
            setattr(environment, self.attribute, value)
