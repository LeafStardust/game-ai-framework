from framework.core.action import Action
from framework.core.state import GameState


class Experience:
    """
    Stores a single agent interaction.
    """

    def __init__(
        self,
        state: GameState,
        action: Action,
        reward: float,
        next_state: GameState
    ):
        self.state: GameState = state
        self.action: Action = action
        self.reward: float = reward
        self.next_state: GameState = next_state