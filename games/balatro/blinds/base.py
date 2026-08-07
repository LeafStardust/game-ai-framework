from abc import ABC, abstractmethod

from framework.core.action import Action
from framework.core.state import GameState


class BlindModifier(ABC):
    """
    Base interface for blind effects.
    """

    @abstractmethod
    def apply(
        self,
        state: GameState,
        action: Action
    ) -> None:
        pass