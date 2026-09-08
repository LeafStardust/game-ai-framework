from abc import ABC, abstractmethod

from games.balatro.actions import BalatroAction
from games.balatro.state import BalatroState
from games.balatro.live.protocol import (
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


class BalatroLiveBridge(ABC):
    """Transport boundary between Python and the live Balatro process."""

    @abstractmethod
    def observe(self) -> LiveBalatroSnapshot:
        pass

    @abstractmethod
    def send(self, command: LiveBalatroCommand) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass


class BalatroStateTranslator(ABC):
    """Converts a live-game snapshot into framework Balatro state."""

    @abstractmethod
    def translate(
        self,
        snapshot: LiveBalatroSnapshot
    ) -> BalatroState:
        pass


class BalatroActionExecutor(ABC):
    """Converts framework actions into commands for the live game bridge."""

    @abstractmethod
    def command_for(
        self,
        action: BalatroAction,
        snapshot: LiveBalatroSnapshot
    ) -> LiveBalatroCommand:
        pass
