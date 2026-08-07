from framework.core.environment import GameEnvironment
from framework.core.action import Action
from framework.core.state import GameState

from games.balatro.state import BalatroState
from games.balatro.actions import (
    BalatroAction,
    PLAY_CARDS,
    DISCARD_CARDS,
    END_ROUND
)
from games.balatro.card_selector import CardSelector


class BalatroEnvironment(GameEnvironment):
    """
    Environment for a Balatro game instance.
    """

    def __init__(self):
        self.state = BalatroState()
        self.card_selector = CardSelector()


    def reset(self) -> None:
        self.state = BalatroState()


    def get_state(self) -> GameState:
        return self.state


    def get_actions(self) -> list[Action]:

        actions = []

        if self.state.phase == "ROUND_START":

            actions.extend(
                self.card_selector.generate_actions(
                    self.state
                )
            )

            actions.append(
                BalatroAction(
                    DISCARD_CARDS
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

        self._apply_action(
            self.state,
            action
        )


    def simulate_action(
        self,
        action: Action
    ) -> GameState:

        simulated_state = self.state.copy()

        self._apply_action(
            simulated_state,
            action
        )

        return simulated_state


    def _apply_action(
        self,
        state: BalatroState,
        action: Action
    ) -> None:

        if action.name == PLAY_CARDS:
            state.round += 1
            state.phase = "ROUND_START"

        elif action.name == DISCARD_CARDS:
            state.discards_remaining -= 1

        elif action.name == END_ROUND:
            state.round += 1
            state.phase = "ROUND_START"


    def is_terminal(self) -> bool:
        return self.state.round >= 3


    def get_reward(self) -> float:
        return float(self.state.score)