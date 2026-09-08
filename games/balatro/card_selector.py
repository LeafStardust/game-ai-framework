from itertools import combinations

from games.balatro.actions import (
    BalatroAction,
    PLAY_CARDS,
    DISCARD_CARDS
)
from games.balatro.state import BalatroState


class CardSelector:

    MAX_SELECTED_CARDS = 5

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

        max_cards = min(
            self.MAX_SELECTED_CARDS,
            len(state.hand)
        )

        for amount in range(1, max_cards + 1):

            for cards in combinations(
                state.hand,
                amount
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

        if state.discards_remaining <= 0:
            return actions

        max_cards = min(
            self.MAX_SELECTED_CARDS,
            len(state.hand)
        )

        for amount in range(1, max_cards + 1):

            for cards in combinations(
                state.hand,
                amount
            ):
                actions.append(
                    BalatroAction(
                        DISCARD_CARDS,
                        cards=list(cards)
                    )
                )

        return actions
