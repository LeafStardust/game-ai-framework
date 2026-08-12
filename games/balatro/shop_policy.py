from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    BalatroAction,
)
from games.balatro.build import (
    ContextualConsumableSynergyEvaluator,
    JokerBuildValueEvaluator,
)
from games.balatro.consumable import PlanetCard
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


class DefaultShopItemValueEstimator:
    """Build-aware value model for currently policy-scoreable shop items.

    Joker utility is delegated to the B3 whole-build evaluator. Consumable base
    heuristics remain conservative, but B4 build-path gain is added generically so
    modeled deck transformations can receive context without item-name combo tables.
    Voucher valuation remains its existing D3 foundation until that layer is split
    into its own dedicated threshold policy.
    """

    def __init__(
        self,
        *,
        joker_build_value: JokerBuildValueEvaluator | None = None,
        consumable_build: ContextualConsumableSynergyEvaluator | None = None,
    ) -> None:
        self.joker_build_value = joker_build_value or JokerBuildValueEvaluator()
        self.consumable_build = (
            consumable_build or ContextualConsumableSynergyEvaluator()
        )

    def estimate(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> tuple[float, tuple[str, ...]]:
        if action.name == BUY_JOKER:
            evaluation = self.joker_build_value.evaluate(state, action.target)
            notes = (
                f"whole-build Joker gain={evaluation.total_gain:.3f}",
                f"representative scoring gain={evaluation.direct_scoring_gain:.6f}",
                f"B3 contextual gain={evaluation.contextual.total_gain:.3f}",
                *evaluation.rationale,
            )
            return evaluation.total_gain, notes

        if action.name == BUY_CONSUMABLE:
            target = action.target
            contextual = self.consumable_build.evaluate(target, state)
            category = str(getattr(target, "category", "")).upper()

            if isinstance(target, PlanetCard) or category == "PLANET":
                chips = float(getattr(target, "chips", 0))
                mult = float(getattr(target, "mult", 0))
                hand_type = getattr(target, "hand_type", None)
                level = state.hand_levels.get(hand_type, 1) if hand_type else 1
                base_value = (
                    2.5
                    + chips * 0.04
                    + mult * 0.30
                    + min(level, 8) * 0.08
                )
                return self._with_consumable_build_path(
                    base_value,
                    (
                        f"planet upgrade chips={chips:g} mult={mult:g}",
                        f"current hand level={level}",
                    ),
                    contextual,
                )

            if category == "SPECTRAL":
                return self._with_consumable_build_path(
                    4.0,
                    ("spectral fallback value",),
                    contextual,
                )

            if category == "TAROT":
                base_value, notes = self._tarot_value(state, target)
                return self._with_consumable_build_path(
                    base_value,
                    notes,
                    contextual,
                )

            return self._with_consumable_build_path(
                2.5,
                ("unknown consumable fallback value",),
                contextual,
            )

        if action.name == BUY_VOUCHER:
            return self._voucher_value(state, action.target)

        return 0.0, ()

    @staticmethod
    def _with_consumable_build_path(
        base_value: float,
        notes: tuple[str, ...],
        contextual,
    ) -> tuple[float, tuple[str, ...]]:
        build_path_gain = float(contextual.build_path_gain)
        extra = [f"B4 build-path gain={build_path_gain:.3f}"]
        extra.extend(path.detail for path in contextual.paths)
        extra.extend(
            contribution.detail
            for contribution in contextual.contributions
            if contribution.kind == "PROSPECTIVE_TRANSFORM"
        )
        return base_value + build_path_gain, notes + tuple(extra)

    def _tarot_value(
        self,
        state: BalatroState,
        target,
    ) -> tuple[float, tuple[str, ...]]:
        name = str(getattr(target, "name", getattr(target, "label", "")))

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

    def _voucher_value(
        self,
        state: BalatroState,
        target,
    ) -> tuple[float, tuple[str, ...]]:
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
