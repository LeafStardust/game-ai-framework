from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Protocol

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    BalatroAction,
)
from games.balatro.card import BalatroCard
from games.balatro.consumable import PlanetCard
from games.balatro.hand import PokerHand
from games.balatro.joker import Joker
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class ShopActionScore:
    """Explainable score for one save-safe shop action."""

    action: BalatroAction
    total: float
    item_utility: float = 0.0
    edition_bonus: float = 0.0
    price_penalty: float = 0.0
    interest_penalty: float = 0.0
    reserve_penalty: float = 0.0
    slot_penalty: float = 0.0
    notes: tuple[str, ...] = ()


class ShopItemValueEstimator(Protocol):

    def estimate(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> tuple[float, tuple[str, ...]]: ...


class JokerMarginalValueEstimator:
    """Estimate direct scoring gain by reusing existing Joker implementations.

    The probes are deterministic and operate on deep-copied state, so stateful
    Jokers cannot mutate the live agent state while being valued.
    """

    PROBES = (
        (
            PokerHand.HIGH_CARD,
            (
                BalatroCard("A", "Spades"),
                BalatroCard("K", "Hearts"),
                BalatroCard("9", "Clubs"),
                BalatroCard("5", "Diamonds"),
                BalatroCard("2", "Spades"),
            ),
        ),
        (
            PokerHand.PAIR,
            (
                BalatroCard("8", "Hearts"),
                BalatroCard("8", "Spades"),
                BalatroCard("K", "Clubs"),
                BalatroCard("7", "Diamonds"),
                BalatroCard("2", "Hearts"),
            ),
        ),
        (
            PokerHand.TWO_PAIR,
            (
                BalatroCard("A", "Hearts"),
                BalatroCard("A", "Spades"),
                BalatroCard("K", "Clubs"),
                BalatroCard("K", "Diamonds"),
                BalatroCard("2", "Hearts"),
            ),
        ),
        (
            PokerHand.THREE_OF_A_KIND,
            (
                BalatroCard("Q", "Hearts"),
                BalatroCard("Q", "Spades"),
                BalatroCard("Q", "Clubs"),
                BalatroCard("7", "Diamonds"),
                BalatroCard("2", "Hearts"),
            ),
        ),
        (
            PokerHand.STRAIGHT,
            (
                BalatroCard("10", "Hearts"),
                BalatroCard("J", "Spades"),
                BalatroCard("Q", "Clubs"),
                BalatroCard("K", "Diamonds"),
                BalatroCard("A", "Hearts"),
            ),
        ),
        (
            PokerHand.FLUSH,
            (
                BalatroCard("A", "Hearts"),
                BalatroCard("10", "Hearts"),
                BalatroCard("8", "Hearts"),
                BalatroCard("5", "Hearts"),
                BalatroCard("2", "Hearts"),
            ),
        ),
        (
            PokerHand.FULL_HOUSE,
            (
                BalatroCard("K", "Hearts"),
                BalatroCard("K", "Spades"),
                BalatroCard("K", "Clubs"),
                BalatroCard("8", "Diamonds"),
                BalatroCard("8", "Hearts"),
            ),
        ),
        (
            PokerHand.FOUR_OF_A_KIND,
            (
                BalatroCard("8", "Hearts"),
                BalatroCard("8", "Spades"),
                BalatroCard("8", "Clubs"),
                BalatroCard("8", "Diamonds"),
                BalatroCard("A", "Hearts"),
            ),
        ),
    )

    def __init__(self, scorer: BalatroScorer | None = None):
        self.scorer = scorer or BalatroScorer()

    def estimate(self, state: BalatroState, joker) -> float:
        if not isinstance(joker, Joker):
            return 0.0

        random_state = random.getstate()
        gains: list[float] = []
        try:
            random.seed(0)
            for hand, cards in self.PROBES:
                before_state = copy.deepcopy(state)
                before_state.hand = list(cards)
                after_state = copy.deepcopy(before_state)
                after_state.jokers.append(copy.deepcopy(joker))

                before = self.scorer.score(
                    hand,
                    state=before_state,
                    cards=list(cards),
                ).total
                after = self.scorer.score(
                    hand,
                    state=after_state,
                    cards=list(cards),
                ).total

                gains.append(
                    max(0.0, (after - before) / max(float(before), 1.0))
                )
        finally:
            random.setstate(random_state)

        if not gains:
            return 0.0
        return sum(gains) / len(gains)


class DefaultShopItemValueEstimator:
    """Conservative intrinsic value model for currently buffer-safe shop items."""

    def __init__(
        self,
        joker_marginal: JokerMarginalValueEstimator | None = None,
        *,
        joker_base_value: float = 4.5,
        direct_gain_weight: float = 6.0,
    ):
        self.joker_marginal = joker_marginal or JokerMarginalValueEstimator()
        self.joker_base_value = joker_base_value
        self.direct_gain_weight = direct_gain_weight

    def estimate(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> tuple[float, tuple[str, ...]]:
        if action.name == BUY_JOKER:
            gain = self.joker_marginal.estimate(state, action.target)
            value = self.joker_base_value + min(12.0, gain * self.direct_gain_weight)
            notes = [f"joker base={self.joker_base_value:.2f}"]
            if gain > 0:
                notes.append(f"direct scoring gain={gain:.3f}")
            else:
                notes.append("no direct HAND_SCORED gain detected")
            return value, tuple(notes)

        if action.name == BUY_CONSUMABLE:
            target = action.target
            category = str(getattr(target, "category", "")).upper()
            if isinstance(target, PlanetCard) or category == "PLANET":
                chips = float(getattr(target, "chips", 0))
                mult = float(getattr(target, "mult", 0))
                hand_type = getattr(target, "hand_type", None)
                level = state.hand_levels.get(hand_type, 1) if hand_type else 1
                value = 2.5 + chips * 0.04 + mult * 0.30 + min(level, 8) * 0.08
                return value, (
                    f"planet upgrade chips={chips:g} mult={mult:g}",
                    f"current hand level={level}",
                )
            if category == "SPECTRAL":
                return 4.0, ("spectral fallback value",)
            if category == "TAROT":
                return 3.2, ("tarot fallback value",)
            return 2.5, ("unknown consumable fallback value",)

        if action.name == BUY_VOUCHER:
            return 6.0, ("persistent voucher fallback value",)

        return 0.0, ()


class BalatroShopPolicy:
    """Rank deterministic shop actions against the option to save money."""

    EDITION_BONUSES = {
        "FOIL": 0.8,
        "HOLOGRAPHIC": 1.5,
        "POLYCHROME": 2.5,
        "NEGATIVE": 4.0,
    }

    def __init__(
        self,
        item_value_estimator: ShopItemValueEstimator | None = None,
        *,
        price_weight: float = 0.35,
        interest_weight: float = 1.25,
        reserve_target: int = 5,
        reserve_weight: float = 0.45,
        last_joker_slot_penalty: float = 1.5,
        penultimate_joker_slot_penalty: float = 0.5,
        last_consumable_slot_penalty: float = 0.6,
        hold_bias: float = 0.35,
    ):
        self.item_value_estimator = (
            item_value_estimator or DefaultShopItemValueEstimator()
        )
        self.price_weight = price_weight
        self.interest_weight = interest_weight
        self.reserve_target = max(0, reserve_target)
        self.reserve_weight = reserve_weight
        self.last_joker_slot_penalty = last_joker_slot_penalty
        self.penultimate_joker_slot_penalty = penultimate_joker_slot_penalty
        self.last_consumable_slot_penalty = last_consumable_slot_penalty
        self.hold_bias = hold_bias

    def choose_action(
        self,
        state: BalatroState,
        actions: list[BalatroAction],
    ) -> BalatroAction:
        ranked = self.rank_actions(state, actions)
        if not ranked:
            raise ValueError("shop policy requires at least one action")
        return ranked[0].action

    def rank_actions(
        self,
        state: BalatroState,
        actions: list[BalatroAction],
    ) -> list[ShopActionScore]:
        if state.phase != "SHOP":
            raise ValueError("shop policy requires SHOP phase")

        scores = [self.score_action(state, action) for action in actions]
        return sorted(
            scores,
            key=lambda result: (
                result.total,
                result.action.name == END_SHOP,
            ),
            reverse=True,
        )

    def score_action(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> ShopActionScore:
        if action.name == END_SHOP:
            return ShopActionScore(
                action=action,
                total=self.hold_bias,
                notes=("hold money / leave shop",),
            )

        if action.name not in {BUY_JOKER, BUY_CONSUMABLE, BUY_VOUCHER}:
            raise ValueError(
                f"shop policy cannot safely score action {action.name!r} yet"
            )

        price = self._price(action.target)
        remaining = state.money - price
        if remaining < 0:
            raise ValueError("shop policy received an unaffordable action")

        item_utility, notes = self.item_value_estimator.estimate(state, action)
        edition_bonus = self._edition_bonus(action.target)
        price_penalty = price * self.price_weight
        interest_penalty = (
            self._interest(state.money) - self._interest(remaining)
        ) * self.interest_weight
        reserve_penalty = self._incremental_reserve_shortfall(
            state.money,
            remaining,
        ) * self.reserve_weight
        slot_penalty = self._slot_penalty(state, action)

        total = (
            item_utility
            + edition_bonus
            - price_penalty
            - interest_penalty
            - reserve_penalty
            - slot_penalty
        )

        return ShopActionScore(
            action=action,
            total=total,
            item_utility=item_utility,
            edition_bonus=edition_bonus,
            price_penalty=price_penalty,
            interest_penalty=interest_penalty,
            reserve_penalty=reserve_penalty,
            slot_penalty=slot_penalty,
            notes=notes,
        )

    @staticmethod
    def _price(item) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _interest(money: int) -> int:
        return min(5, max(0, int(money)) // 5)

    def _incremental_reserve_shortfall(self, before: int, after: int) -> int:
        before_shortfall = max(0, self.reserve_target - before)
        after_shortfall = max(0, self.reserve_target - after)
        return max(0, after_shortfall - before_shortfall)

    def _slot_penalty(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> float:
        if action.name == BUY_JOKER:
            free_after = state.joker_slots - (len(state.jokers) + 1)
            if free_after <= 0:
                return self.last_joker_slot_penalty
            if free_after == 1:
                return self.penultimate_joker_slot_penalty
            return 0.0

        if action.name == BUY_CONSUMABLE:
            free_after = state.consumable_slots - (len(state.consumables) + 1)
            if free_after <= 0:
                return self.last_consumable_slot_penalty

        return 0.0

    def _edition_bonus(self, item) -> float:
        edition = getattr(item, "edition", None)
        if isinstance(edition, dict):
            for name, enabled in edition.items():
                if enabled:
                    edition = name
                    break
            else:
                edition = None
        if not edition:
            return 0.0
        return self.EDITION_BONUSES.get(str(edition).upper(), 0.0)
