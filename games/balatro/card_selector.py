from itertools import combinations

from games.balatro.actions import (
    BalatroAction,
    PLAY_CARDS,
    DISCARD_CARDS
)
from games.balatro.state import BalatroState


class CardSelector:
    """
    Generates possible card selections for Balatro actions.
    """

    def generate_actions(
        self,
        state: BalatroState
    ) -> list[BalatroAction]:

        actions = []

        actions.extend(
            self.generate_play_actions(
                state
            )
        )

        actions.extend(
            self.generate_discard_actions(
                state
            )
        )

        return actions


    def generate_play_actions(
        self,
        state: BalatroState
    ) -> list[BalatroAction]:

        actions = []

        for cards in combinations(
            state.hand,
            5
        ):
            actions.append(
                BalatroAction(
                    PLAY_CARDS,
                    cards=list(cards)
                )
            )

        return actions


    def generate_discard_actions(
        self,
        state: BalatroState
    ) -> list[BalatroAction]:

        actions = []

        for cards in combinations(
            state.hand,
            1
        ):
            actions.append(
                BalatroAction(
                    DISCARD_CARDS,
                    cards=list(cards)
                )
            )

        return actions