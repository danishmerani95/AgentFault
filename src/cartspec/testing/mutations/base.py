from abc import ABC, abstractmethod

from cartspec.commerce.environment import CommerceEnvironment


class Mutation(ABC):
    @abstractmethod
    def apply(self, environment: CommerceEnvironment) -> None:
        raise NotImplementedError
