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
from games.balatro.joker import Joker, JokerContext
from games.balatro.scoring import BalatroScorer, HandScore
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


@dataclass(frozen=True)
class JokerProbeResult:
    """Observable consequences detected from an existing Joker implementation."""

    direct_scoring_gain: float = 0.0
    semantic_signals: tuple[str, ...] = ()


class ShopItemValueEstimator(Protocol):

    def estimate(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> tuple[float, tuple[str, ...]]: ...


class JokerMarginalValueEstimator:
    """Reuse existing Joker implementations to estimate immediate and semantic value.

    Scoring probes compare representative hands with and without the candidate Joker.
    A separate semantic probe captures framework signals written to JokerContext.data,
    which is important for effect Jokers such as Mime that do not directly modify the
    HandScore object.
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
        return self.analyze(state, joker).direct_scoring_gain

    def analyze(self, state: BalatroState, joker) -> JokerProbeResult:
        if not isinstance(joker, Joker):
            return JokerProbeResult()

        random_state = random.getstate()
        gains: list[float] = []
        signals: set[str] = set()
        try:
            random.seed(0)
            for hand, cards in self.PROBES:
                before_state = copy.deepcopy(state)
                before_state.hand = list(cards)
                after_state = copy.deepcopy(before_state)
                after_state.jokers.append(copy.deepcopy(joker))

                try:
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
                except (AttributeError, KeyError, TypeError, ValueError):
                    # Some event-specific Jokers require context that a scoring probe
                    # intentionally does not fabricate. They are handled conservatively.
                    continue

                gains.append(
                    max(0.0, (after - before) / max(float(before), 1.0))
                )

                signals.update(self._semantic_signals(joker, before_state, hand, cards))
        finally:
            random.setstate(random_state)

        gain = sum(gains) / len(gains) if gains else 0.0
        return JokerProbeResult(
            direct_scoring_gain=gain,
            semantic_signals=tuple(sorted(signals)),
        )

    @staticmethod
    def _semantic_signals(joker, state, hand, cards) -> set[str]:
        probe = copy.deepcopy(joker)
        context = JokerContext(
            state=copy.deepcopy(state),
            score=HandScore(50, 5),
            poker_hand=hand,
            cards=list(cards),
            held_cards=list(cards),
            trigger="HAND_SCORED",
            data={},
        )
        try:
            result = probe.apply(context)
        except (AttributeError, KeyError, TypeError, ValueError):
            return set()

        data = getattr(result, "data", {}) or {}
        return {
            str(key)
            for key, value in data.items()
            if value not in (None, False, 0, "", [], {}, ())
        }


class DefaultShopItemValueEstimator:
    """Conservative intrinsic value model for currently buffer-safe shop items."""

    def __init__(
        self,
        joker_marginal: JokerMarginalValueEstimator | None = None,
        *,
        joker_base_value: float = 2.25,
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
            analysis = self.joker_marginal.analyze(state, action.target)
            gain = analysis.direct_scoring_gain
            semantic_bonus, semantic_notes = self._semantic_joker_value(
                state,
                action.target,
                analysis.semantic_signals,
            )
            value = (
                self.joker_base_value
                + min(12.0, gain * self.direct_gain_weight)
                + semantic_bonus
            )
            notes = [f"joker base={self.joker_base_value:.2f}"]
            if gain > 0:
                notes.append(f"direct scoring gain={gain:.3f}")
            else:
                notes.append("no direct HAND_SCORED gain detected")
            notes.extend(semantic_notes)
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
                return self._tarot_value(state, target)
            return 2.5, ("unknown consumable fallback value",)

        if action.name == BUY_VOUCHER:
            return self._voucher_value(state, action.target)

        return 0.0, ()

    def _semantic_joker_value(
        self,
        state: BalatroState,
        joker,
        signals: tuple[str, ...],
    ) -> tuple[float, list[str]]:
        bonus = 0.0
        notes: list[str] = []

        if "retrigger_held_abilities" in signals:
            held_sources = self._held_ability_sources(state)
            baron = any(
                type(owned).__name__ == "BaronJoker"
                for owned in state.jokers
            )
            prospective_steel = self._has_consumable_named(
                state.shop_consumables,
                "The Chariot",
            ) or self._has_consumable_named(
                state.consumables,
                "The Chariot",
            )

            bonus += 0.35
            if held_sources:
                bonus += min(4.0, held_sources * 0.85)
            if baron:
                bonus += 3.0
            if prospective_steel:
                bonus += 1.0

            notes.append(
                "held-ability retrigger signal: "
                f"deck sources={held_sources}"
            )
            if baron:
                notes.append("Baron synergy detected")
            if prospective_steel:
                notes.append("Chariot/Steel setup synergy detected")

        unknown_signals = [
            signal
            for signal in signals
            if signal != "retrigger_held_abilities"
        ]
        if unknown_signals:
            bonus += min(1.0, len(unknown_signals) * 0.25)
            notes.append(
                "effect signals=" + ",".join(sorted(unknown_signals))
            )

        return bonus, notes

    def _tarot_value(self, state: BalatroState, target) -> tuple[float, tuple[str, ...]]:
        name = str(getattr(target, "name", getattr(target, "label", "")))

        if name == "The Chariot":
            mime_owned = any(
                type(joker).__name__ == "MimeJoker"
                for joker in state.jokers
            )
            mime_available = any(
                type(joker).__name__ == "MimeJoker"
                or str(getattr(joker, "label", "")) == "Mime"
                for joker in state.shop_jokers
            )
            value = 3.9
            notes = ["Chariot creates a persistent Steel card"]
            if mime_owned:
                value += 2.0
                notes.append("owned Mime retrigger synergy")
            elif mime_available:
                value += 1.0
                notes.append("shop Mime combo opportunity")
            return value, tuple(notes)

        if name == "The Hermit":
            gain = max(0, min(state.money * 2, 20) - state.money)
            value = 2.2 + min(5.0, gain * 0.35)
            return value, (f"Hermit potential money gain={gain}",)

        if name == "Judgement":
            free = max(0, state.joker_slots - len(state.jokers))
            value = 4.5 if free > 0 else 0.5
            return value, (f"free joker slots={free}",)

        if name == "The Wheel of Fortune":
            value = 3.4 if state.jokers else 1.0
            return value, ("edition chance requires owned Joker",)

        return 3.2, ("tarot fallback value",)

    def _voucher_value(self, state: BalatroState, target) -> tuple[float, tuple[str, ...]]:
        label = str(getattr(target, "label", getattr(target, "name", "")))

        if label == "Hieroglyph":
            # Extra ante runway is strategically useful, but losing one hand every
            # round is a substantial survivability cost. Keep this conservative.
            runway_bonus = max(0.0, 4.0 - min(float(state.ante), 4.0)) * 0.25
            value = 4.0 + runway_bonus
            return value, (
                "Hieroglyph: -1 Ante / -1 hand each round",
                f"ante={state.ante} heuristic runway bonus={runway_bonus:.2f}",
            )

        if label == "Antimatter":
            return 10.0, ("Antimatter grants +1 Joker slot",)

        if label in {"Paint Brush", "Palette"}:
            return 7.0, ("permanent +1 hand size",)

        if label in {"Grabber", "Nacho Tong"}:
            return 7.0, ("permanent +1 hand per round",)

        if label in {"Wasteful", "Recyclomancy"}:
            return 5.5, ("permanent +1 discard per round",)

        if label == "Seed Money":
            value = 3.0 + min(4.0, max(0, state.money - 20) * 0.15)
            return value, ("raises interest cap to $10",)

        if label == "Money Tree":
            value = 4.5 + min(5.0, max(0, state.money - 25) * 0.15)
            return value, ("raises interest cap to $20",)

        if label == "Blank":
            return 0.5, ("Blank has no immediate run effect",)

        return 5.0, ("persistent voucher conservative fallback value",)

    @staticmethod
    def _held_ability_sources(state: BalatroState) -> int:
        cards = list(getattr(state, "deck", []))
        return sum(
            getattr(card, "enhancement", None) in {"Steel", "Gold"}
            or getattr(card, "seal", None) == "Blue"
            for card in cards
        )

    @staticmethod
    def _has_consumable_named(items, name: str) -> bool:
        return any(
            str(getattr(item, "name", getattr(item, "label", ""))) == name
            for item in items
        )


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
