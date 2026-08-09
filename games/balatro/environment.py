import random

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
from games.balatro.blinds.manager import BlindManager
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer


class BalatroEnvironment(GameEnvironment):

    def __init__(self):

        self.state = BalatroState()

        self.card_selector = CardSelector()
        self.blind_manager = BlindManager()

        self.hand_evaluator = HandEvaluator()
        self.scorer = BalatroScorer()

        self.rng = random.Random()

        self.rng.shuffle(
            self.state.deck
        )

        self._draw_cards(
            self.state,
            8
        )

        self._setup_blind()


    def reset(self) -> None:

        self.state = BalatroState()

        self.rng.shuffle(
            self.state.deck
        )

        self._draw_cards(
            self.state,
            8
        )

        self._setup_blind()


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

        simulated_environment = self.copy()

        simulated_environment._apply_action(
            simulated_environment.state,
            action.copy()
        )

        return simulated_environment.state


    def copy(self):

        new_environment = object.__new__(
            BalatroEnvironment
        )

        new_environment.state = self.state.copy()

        new_environment.card_selector = self.card_selector
        new_environment.blind_manager = self.blind_manager

        new_environment.hand_evaluator = self.hand_evaluator
        new_environment.scorer = self.scorer

        new_environment.rng = random.Random()

        new_environment.rng.setstate(
            self.rng.getstate()
        )

        return new_environment


    def _initialize_deck(self):

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

        self.state.deck = [
            BalatroCard(rank, suit)
            for rank in ranks
            for suit in suits
        ]

        self.rng.shuffle(
            self.state.deck
        )


    def _setup_blind(self) -> None:

        if self.state.round == 1:

            blind_type = "SMALL"

        elif self.state.round == 2:

            blind_type = "BIG"

        else:

            blind_type = "BOSS"


        self.state.blind = self.blind_manager.get_blind(
            blind_type,
            self.state.ante
        )


        if hasattr(
            self.state.blind,
            "name"
        ):

            self.state.boss_name = self.state.blind.name

        else:

            self.state.boss_name = None


    def _complete_blind(
        self,
        state: BalatroState
    ) -> None:

        state.blind_score = 0

        state.round += 1

        if state.round > 3:

            state.ante += 1
            state.round = 1

        state.phase = "ROUND_START"

        self._setup_blind()


    def _apply_action(
        self,
        state: BalatroState,
        action: Action
    ) -> None:

        if action.name == PLAY_CARDS:

            modified_action = action.copy()

            if state.blind:

                if not state.blind.apply_modifiers(
                    state,
                    modified_action
                ):
                    return


            selected_cards = getattr(
                modified_action,
                "cards",
                []
            )


            if selected_cards:

                poker_hand = self.hand_evaluator.evaluate(
                    selected_cards
                )

                hand_score = self.scorer.score(
                    poker_hand,
                    state,
                    selected_cards
                )

                state.score += hand_score.total
                state.blind_score += hand_score.total


                for card in selected_cards:

                    if card in state.hand:

                        state.hand.remove(card)

                        state.discard_pile.append(
                            card
                        )


            if state.blind_score >= state.blind.requirement:

                self._complete_blind(
                    state
                )

            else:

                state.round += 1
                state.phase = "ROUND_START"



        elif action.name == DISCARD_CARDS:

            state.discards_remaining -= 1

            selected_cards = getattr(
                action,
                "cards",
                []
            )


            for card in selected_cards:

                if card in state.hand:

                    state.hand.remove(card)

                    state.discard_pile.append(
                        card
                    )


            self._draw_cards(
                state,
                len(selected_cards)
            )



        elif action.name == END_ROUND:

            state.round += 1

            state.phase = "ROUND_START"

            self._setup_blind()



    def _draw_cards(
        self,
        state: BalatroState,
        amount: int
    ) -> None:

        draw_amount = min(
            amount,
            len(state.deck)
        )

        for _ in range(draw_amount):

            state.hand.append(
                state.deck.pop()
            )


    def is_terminal(self) -> bool:

        return self.state.ante > 8


    def get_reward(self) -> float:

        return float(
            self.state.score
        )