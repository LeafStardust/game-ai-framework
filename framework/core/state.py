from abc import ABC


class GameState(ABC):
    """
    Represents the current state of any game.

    Game-specific states should inherit from this.
    """

    def copy(self):
        """
        Creates an independent copy of the state.

        Games requiring simulation should override this method.
        """

        raise NotImplementedError(
            "This game state does not support copying."
        )