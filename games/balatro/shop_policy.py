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
    JokerBuildTransition,
    JokerBuildTransitionPlanner,
    JokerBuildValueEvaluator,
    JokerReplacementOption,
)
from games.balatro.consumable import PlanetCard
from games.balatro.joker import Joker
from games.balatro.joker_edition import (
    EDITION_UNIVERSAL_VALUES,
    joker_edition_universal_value,
    joker_has_negative_edition,
)
from games.balatro.resource_value import RunResourceValuator
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
class ShopJokerRecommendation:
    """Build/economy recommendation for one observable shop Joker.

    ``BUY`` is the only result that carries an executable action. ``REPLACE`` is
    deliberately advisory until Joker sell/replace execution exists; its replacement
    option exposes the whole-build delta and the exact incumbent slot. ``HOLD`` means
    the candidate should not be bought under the current build/economy state.
    """

    decision: str
    candidate: object
    build_transition: JokerBuildTransition
    executable_action: BalatroAction | None = None
    shop_score: ShopActionScore | None = None
    replacement: JokerReplacementOption | None = None
    rationale: tuple[str, ...] = ()


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
            gain = min(max(0, int(state.money)), 20)
            value = 2.2 + min(5.0, gain * 0.35)
            return value, (f"Hermit deterministic money gain={gain}",)

        if name == "Temperance":
            joker_sell_value = sum(
                max(0, int(getattr(joker, "sell_value", 0)))
                for joker in state.jokers
            )
            gain = min(joker_sell_value, 50)
            value = 2.2 + min(5.0, gain * 0.35)
            return value, (
                f"Temperance deterministic money gain={gain}",
                f"public Joker sell value={joker_sell_value}",
            )

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

    EDITION_BONUSES = EDITION_UNIVERSAL_VALUES

    def __init__(
        self,
        item_value_estimator: ShopItemValueEstimator | None = None,
        *,
        joker_transition_planner: JokerBuildTransitionPlanner | None = None,
        resource_valuator: RunResourceValuator | None = None,
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
        self.resource_valuator = resource_valuator or RunResourceValuator()
        if joker_transition_planner is not None:
            self.joker_transition_planner = joker_transition_planner
        elif isinstance(self.item_value_estimator, DefaultShopItemValueEstimator):
            self.joker_transition_planner = JokerBuildTransitionPlanner(
                evaluator=self.item_value_estimator.joker_build_value,
            )
        else:
            self.joker_transition_planner = JokerBuildTransitionPlanner()
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

        scores: list[ShopActionScore] = []
        for action in actions:
            if action.name == BUY_JOKER and isinstance(action.target, Joker):
                recommendation = self.recommend_joker(state, action.target)
                if recommendation.decision != "BUY":
                    continue
                if recommendation.shop_score is None:
                    raise RuntimeError("BUY Joker recommendation is missing its shop score")
                scores.append(recommendation.shop_score)
                continue
            scores.append(self.score_action(state, action))

        return sorted(
            scores,
            key=lambda result: (
                result.total,
                result.action.name == END_SHOP,
            ),
            reverse=True,
        )

    def recommend_jokers(
        self,
        state: BalatroState,
    ) -> tuple[ShopJokerRecommendation, ...]:
        """Evaluate all observable shop Jokers, including full-row replacements."""
        if state.phase != "SHOP":
            raise ValueError("shop policy requires SHOP phase")
        return tuple(
            self.recommend_joker(state, candidate)
            for candidate in state.shop_jokers
        )

    def recommend_joker(
        self,
        state: BalatroState,
        candidate: object,
    ) -> ShopJokerRecommendation:
        """Map build transition semantics onto safe shop-level Joker advice.

        A slot-safe ``ADD`` may become an executable ``BUY`` after ordinary shop
        economics are checked. This includes a Negative Joker on a full ordinary
        roster. A build ``HOLD`` is rejected. A ``REPLACE`` exposes the best
        incumbent and whole-build delta but never synthesizes a direct buy, sell, or
        compound action.
        """
        if state.phase != "SHOP":
            raise ValueError("shop policy requires SHOP phase")

        transition = self.joker_transition_planner.plan(state, candidate)

        if transition.action == "HOLD":
            return ShopJokerRecommendation(
                decision="HOLD",
                candidate=candidate,
                build_transition=transition,
                rationale=transition.rationale,
            )

        if transition.action == "REPLACE":
            replacement = transition.replacement
            replacement_notes = replacement.rationale if replacement is not None else ()
            return ShopJokerRecommendation(
                decision="REPLACE",
                candidate=candidate,
                build_transition=transition,
                replacement=replacement,
                rationale=(
                    *transition.rationale,
                    *replacement_notes,
                    "replacement is advisory only; sell/buy execution is not enabled",
                ),
            )

        if transition.action != "ADD":
            raise ValueError(
                f"unsupported Joker build transition {transition.action!r}"
            )

        price = self._price(candidate)
        if state.money < price:
            return ShopJokerRecommendation(
                decision="HOLD",
                candidate=candidate,
                build_transition=transition,
                rationale=(
                    *transition.rationale,
                    f"candidate costs ${price} but only ${state.money} is available",
                ),
            )

        action = BalatroAction(BUY_JOKER, target=candidate)
        shop_score = self.score_action(state, action)
        if shop_score.total <= self.hold_bias:
            return ShopJokerRecommendation(
                decision="HOLD",
                candidate=candidate,
                build_transition=transition,
                shop_score=shop_score,
                rationale=(
                    *transition.rationale,
                    *shop_score.notes,
                    f"shop score={shop_score.total:.3f} does not beat "
                    f"hold={self.hold_bias:.3f}",
                ),
            )

        return ShopJokerRecommendation(
            decision="BUY",
            candidate=candidate,
            build_transition=transition,
            executable_action=action,
            shop_score=shop_score,
            rationale=(
                *transition.rationale,
                *shop_score.notes,
                f"shop score={shop_score.total:.3f} beats hold={self.hold_bias:.3f}",
            ),
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

        if (
            action.name == BUY_JOKER
            and len(state.jokers) >= state.joker_slots
            and not joker_has_negative_edition(action.target)
        ):
            raise ValueError(
                "direct BUY_JOKER requires a free Joker slot unless the candidate "
                "is Negative; use recommend_joker() for advisory replacement planning"
            )

        price = self._price(action.target)
        remaining = state.money - price
        if remaining < 0:
            raise ValueError("shop policy received an unaffordable action")

        item_utility, notes = self.item_value_estimator.estimate(state, action)
        edition_bonus = self._edition_bonus(action.target)
        resource_cost = self.resource_valuator.money_spend_cost(
            money=state.money,
            spend=price,
            price_weight=self.price_weight,
            interest_weight=self.interest_weight,
            reserve_target=self.reserve_target,
            reserve_weight=self.reserve_weight,
        )
        price_penalty = resource_cost.direct
        interest_penalty = resource_cost.interest
        reserve_penalty = resource_cost.reserve
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
        return RunResourceValuator.interest_value(money)

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
            if joker_has_negative_edition(action.target):
                return 0.0
            return self.resource_valuator.slot_opportunity_cost(
                occupied=len(state.jokers),
                capacity=state.joker_slots,
                last_slot_penalty=self.last_joker_slot_penalty,
                penultimate_slot_penalty=self.penultimate_joker_slot_penalty,
                resource="joker",
            ).total

        if action.name == BUY_CONSUMABLE:
            return self.resource_valuator.slot_opportunity_cost(
                occupied=len(state.consumables),
                capacity=state.consumable_slots,
                last_slot_penalty=self.last_consumable_slot_penalty,
                penultimate_slot_penalty=0.0,
                resource="consumable",
            ).total

        return 0.0

    def _edition_bonus(self, item) -> float:
        return joker_edition_universal_value(item)
