from __future__ import annotations

import random

from framework.core.action import Action
from framework.core.environment import GameEnvironment
from framework.core.state import GameState

from games.balatro.actions import (
    BalatroAction,
    BUY_CONSUMABLE,
    DISCARD_CARDS,
    END_ROUND,
    END_SHOP,
    PLAY_CARDS,
    REFRESH_SHOP,
    USE_CONSUMABLE,
)
from games.balatro.blinds.manager import BlindManager
from games.balatro.card import BalatroCard
from games.balatro.card_selector import CardSelector
from games.balatro.consumable import ConsumableContext
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.joker import JokerContext
from games.balatro.planets import PLANET_CARDS, create_planet, random_planet
from games.balatro.scoring import BalatroScorer
from games.balatro.spectrals import random_spectral
from games.balatro.state import BalatroState
from games.balatro.tarots import random_tarot


class BalatroEnvironment(GameEnvironment):

    SHOP_REFRESH_COST = 5

    def __init__(self):

        self.state = BalatroState()
        self.card_selector = CardSelector()
        self.blind_manager = BlindManager()
        self.hand_evaluator = HandEvaluator()
        self.scorer = BalatroScorer()
        self.rng = random.Random()
        self.hand_size: int = 8

        self.rng.shuffle(
            self.state.deck
        )

        self._draw_cards(
            self.state,
            self.hand_size
        )

        self._setup_blind()

    def reset(self) -> None:

        self.state = BalatroState()

        self.rng.shuffle(
            self.state.deck
        )

        self._draw_cards(
            self.state,
            self.hand_size
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

            for consumable in self.state.consumables:

                for cards in consumable.get_target_cards(
                    self.state
                ):

                    context = ConsumableContext(
                        state=self.state,
                        cards=cards,
                        target=consumable
                    )

                    if not consumable.can_use(context):
                        continue

                    actions.append(
                        BalatroAction(
                            USE_CONSUMABLE,
                            cards=cards,
                            target=consumable
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

        if self.state.phase == "SHOP":

            actions.extend(
                BalatroAction(
                    BUY_CONSUMABLE,
                    target=consumable
                )
                for consumable in self.state.shop_consumables
                if len(self.state.consumables) < self.state.consumable_slots
                and self.state.money >= consumable.price
            )

            if self.state.money >= self.SHOP_REFRESH_COST:

                actions.append(
                    BalatroAction(
                        REFRESH_SHOP
                    )
                )

            actions.append(
                BalatroAction(
                    END_SHOP
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
        new_environment.hand_size = self.hand_size

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

        self._resolve_end_round_seals(state)

        state.blind_score = 0

        state.round += 1

        if state.round > 3:

            state.ante += 1
            state.round = 1

        self._setup_blind()

        self._generate_shop_consumables(
            state
        )

        state.phase = "SHOP"

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

                state.last_played_hand = poker_hand.value

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

            self._trigger_discard_seals(
                state,
                selected_cards
            )

            for card in selected_cards:

                if card in state.hand:

                    state.hand.remove(card)

                    state.discard_pile.append(
                        card
                    )

            self._trigger_joker_event(
                state,
                BalatroEvent(
                    BalatroEventType.CARDS_DISCARDED,
                    selected_cards
                )
            )

            self._draw_cards(
                state,
                len(selected_cards)
            )

        elif action.name == REFRESH_SHOP:

            if state.phase != "SHOP":
                return

            if state.money < self.SHOP_REFRESH_COST:
                return

            state.money -= self.SHOP_REFRESH_COST

            self._generate_shop_consumables(
                state
            )

        elif action.name == END_SHOP:

            if state.phase != "SHOP":
                return

            state.shop_active = False
            state.phase = "ROUND_START"

        elif action.name == BUY_CONSUMABLE:

            if state.phase != "SHOP":
                return

            consumable = getattr(
                action,
                "target",
                None
            )

            if consumable not in state.shop_consumables:
                return

            if state.money < consumable.price:
                return

            if not state.add_consumable(
                consumable
            ):
                return

            state.money -= consumable.price

            state.shop_consumables.remove(
                consumable
            )

        elif action.name == USE_CONSUMABLE:

            consumable = getattr(
                action,
                "target",
                None
            )

            if consumable not in state.consumables:
                return

            context = ConsumableContext(
                state=state,
                cards=action.cards,
                target=consumable
            )

            if not consumable.can_use(context):
                return

            consumable.use(context)
            state.remove_consumable(consumable)

        elif action.name == END_ROUND:

            self._resolve_end_round_seals(state)

            state.round += 1

            state.phase = "ROUND_START"

            self._setup_blind()

    def _trigger_discard_seals(
        self,
        state: BalatroState,
        cards: list[BalatroCard]
    ) -> None:

        for card in cards:

            if card not in state.hand:
                continue

            if card.seal == "Purple":

                if len(state.consumables) < state.consumable_slots:
                    state.consumables.append(
                        random_tarot(self.rng)
                    )

    def _resolve_end_round_seals(
        self,
        state: BalatroState
    ) -> None:

        for card in state.hand:

            if card.seal == "Gold":
                state.money += 3

            elif card.seal == "Blue":

                if (
                    state.last_played_hand is not None
                    and len(state.consumables) < state.consumable_slots
                ):
                    planet = next(
                        (
                            name
                            for name, value in PLANET_CARDS.items()
                            if value.hand_type == state.last_played_hand
                        ),
                        None
                    )

                    if planet is not None:
                        state.consumables.append(
                            create_planet(planet)
                        )

    def _trigger_joker_event(
        self,
        state: BalatroState,
        event: BalatroEvent
    ) -> None:

        context = JokerContext(
            state=state,
            held_cards=state.hand.copy(),
            trigger=event.type.value,
            event=event
        )

        for joker in state.jokers:

            joker.apply(
                context
            )

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

    def _generate_planet(self):

        return random_planet(
            self.rng
        )

    def _generate_consumable(self):

        roll = self.rng.random()

        if roll < 1 / 3:
            return self._generate_planet()

        if roll < 2 / 3:
            return random_tarot(self.rng)

        return random_spectral(self.rng)

    def _generate_shop_consumables(
        self,
        state: BalatroState
    ) -> None:

        state.shop_consumables = [
            self._generate_consumable(),
            self._generate_consumable()
        ]

        state.shop_active = True

    def is_terminal(self) -> bool:

        return self.state.ante > 8

    def get_reward(self) -> float:

        return float(
            self.state.score
        )