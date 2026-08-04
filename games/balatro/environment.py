from framework.core.environment import GameEnvironment
from framework.core.action import Action
from framework.core.state import GameState

from games.balatro.state import BalatroState
from games.balatro.actions import (
    BalatroAction,
    PLAY_HAND,
    DISCARD_HAND,
    END_ROUND
)


class BalatroEnvironment(GameEnvironment):
    """
    Environment for a Balatro game instance.
    """

    def __init__(self):
        self.state = BalatroState()


    def reset(self) -> None:
        self.state = BalatroState()


    def get_state(self) -> GameState:
        return self.state


    def get_actions(self) -> list[Action]:

        actions = []

        if self.state.phase == "ROUND_START":

            actions.append(
                BalatroAction(
                    PLAY_HAND
                )
            )

            actions.append(
                BalatroAction(
                    DISCARD_HAND
                )
            )

            actions.append(
                BalatroAction(
                    END_ROUND
                )
            )

        return actions


    def execute_action(
        self,
        action: Action
    ) -> None:

        if action.name == PLAY_HAND:
            self.state.phase = "ROUND_END"

        elif action.name == DISCARD_HAND:
            self.state.discard_count += 1

        elif action.name == END_ROUND:
            self.state.round += 1
            self.state.phase = "ROUND_START"


    def is_terminal(self) -> bool:
        return False


    def get_reward(self) -> float:
        return float(self.state.score)