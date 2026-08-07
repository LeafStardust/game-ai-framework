from abc import ABC, abstractmethod

from framework.core.action import Action
from framework.core.state import GameState


class BlindModifier(ABC):

    @abstractmethod
    def apply(
        self,
        state: GameState,
        action: Action
    ) -> bool:
        pass