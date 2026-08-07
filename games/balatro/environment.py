from random import sample

from framework.core.environment import GameEnvironment
from framework.core.action import Action
from framework.core.state import GameState

from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState
from games.balatro.actions import (
    BalatroAction,
    PLAY_CARDS,
    DISCARD_CARDS,
    END_ROUND
)
from games.balatro.card_selector import CardSelector
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer


class BalatroEnvironment(GameEnvironment):
    """
    Environment for a Balatro game instance.
    """

    def __init__(self):
        self.state = BalatroState()
        self.card_selector = CardSelector()

        self.hand_evaluator = HandEvaluator()
        self.scorer = BalatroScorer()


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

            selected_cards = getattr(
                action,
                "cards",
                []
            )

            if selected_cards:

                poker_hand = self.hand_evaluator.evaluate(
                    selected_cards
                )

                hand_score = self.scorer.score(
                    poker_hand
                )

                state.score += hand_score.total

                state.hand = [
                    card
                    for card in state.hand
                    if card not in selected_cards
                ]

            state.round += 1
            state.phase = "ROUND_START"


        elif action.name == DISCARD_CARDS:

            state.discards_remaining -= 1

            selected_cards = getattr(
                action,
                "cards",
                []
            )

            if selected_cards:

                state.hand = [
                    card
                    for card in state.hand
                    if card not in selected_cards
                ]

                self._draw_cards(
                    state,
                    len(selected_cards)
                )


        elif action.name == END_ROUND:

            state.round += 1
            state.phase = "ROUND_START"


    def _draw_cards(
        self,
        state: BalatroState,
        amount: int
    ) -> None:

        ranks = [
            "2", "3", "4", "5", "6",
            "7", "8", "9", "10",
            "J", "Q", "K", "A"
        ]

        suits = [
            "Hearts",
            "Diamonds",
            "Clubs",
            "Spades"
        ]

        deck = [
            BalatroCard(rank, suit)
            for rank in ranks
            for suit in suits
        ]

        available = [
            card
            for card in deck
            if card not in state.hand
        ]

        drawn = sample(
            available,
            min(amount, len(available))
        )

        state.hand.extend(drawn)


    def is_terminal(self) -> bool:
        return self.state.round >= 3


    def get_reward(self) -> float:
        return float(self.state.score)