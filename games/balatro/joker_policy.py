from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker import Joker
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.state import BalatroState


BUY = "BUY"
REPLACE = "REPLACE"
HOLD = "HOLD"


@dataclass(frozen=True)
class JokerAcquisitionThresholds:
    """Thresholds owned only by D2 Joker acquisition/replacement decisions."""

    minimum_purchase_build_gain: float = 0.0
    minimum_purchase_advantage: float = 0.35
    minimum_replacement_build_delta: float = 0.0
    minimum_replacement_advantage: float = 0.75
    price_weight: float = 0.35
    interest_weight: float = 1.25
    reserve_target: int = 5
    reserve_weight: float = 0.45
    last_joker_slot_penalty: float = 1.5
    penultimate_joker_slot_penalty: float = 0.5

    def __post_init__(self) -> None:
        nonnegative = (
            "minimum_purchase_build_gain",
            "minimum_purchase_advantage",
            "minimum_replacement_build_delta",
            "minimum_replacement_advantage",
            "price_weight",
            "interest_weight",
            "reserve_weight",
            "last_joker_slot_penalty",
            "penultimate_joker_slot_penalty",
        )
        for name in nonnegative:
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.reserve_target) < 0:
            raise ValueError("reserve_target cannot be negative")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "JokerAcquisitionThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D2 Joker threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class JokerTransactionEconomics:
    price: int
    sell_credit: int
    net_spend: int
    money_after: int
    edition_delta: float
    price_penalty: float
    interest_penalty: float
    reserve_penalty: float
    slot_penalty: float

    @property
    def total_adjustment(self) -> float:
        return (
            self.edition_delta
            - self.price_penalty
            - self.interest_penalty
            - self.reserve_penalty
            - self.slot_penalty
        )


@dataclass(frozen=True)
class JokerAcquisitionOption:
    mode: str
    build_gain: float
    total_advantage: float
    economics: JokerTransactionEconomics
    eligible: bool
    replace_index: int | None = None
    replace_joker: str | None = None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class JokerAcquisitionDecision:
    action: str
    candidate: str
    selected: JokerAcquisitionOption | None
    options: tuple[JokerAcquisitionOption, ...]
    thresholds: JokerAcquisitionThresholds
    rationale: tuple[str, ...] = ()


class JokerAcquisitionPolicy:
    """D2 build-aware Joker buy/replace decision with explicit HOLD baseline.

    B3/build strategy supplies whole-build gain. D2 adds only transaction economics,
    slot opportunity cost and its own thresholds. A REPLACE recommendation remains
    strategy output only; the autonomous shop layer executes one SELL, then requires
    a fresh authoritative observation and D2 replan before any BUY can be emitted.

    Negative Jokers are slot-neutral in Balatro. They are therefore scored as an
    ADD/BUY even when the ordinary Joker roster is full and never pay ordinary
    Joker-slot opportunity cost.
    """

    EDITION_BONUSES = {
        "FOIL": 0.8,
        "HOLOGRAPHIC": 1.5,
        "POLYCHROME": 2.5,
        "NEGATIVE": 4.0,
    }

    def __init__(
        self,
        thresholds: JokerAcquisitionThresholds | None = None,
        *,
        transition_planner: JokerBuildTransitionPlanner | None = None,
    ) -> None:
        self.thresholds = thresholds or JokerAcquisitionThresholds()
        self.transition_planner = transition_planner or JokerBuildTransitionPlanner(
            minimum_add_gain=0.0,
            minimum_replacement_delta=0.0,
        )

    def decide(
        self,
        state: BalatroState,
        candidate: object,
    ) -> JokerAcquisitionDecision:
        candidate_name = type(candidate).__name__
        if not isinstance(candidate, Joker):
            return JokerAcquisitionDecision(
                action=HOLD,
                candidate=candidate_name,
                selected=None,
                options=(),
                thresholds=self.thresholds,
                rationale=("candidate is not a modeled Joker",),
            )

        transition = self.transition_planner.plan(state, candidate)
        slot_neutral = joker_has_negative_edition(candidate)
        if len(state.jokers) < int(state.joker_slots) or slot_neutral:
            option = self._score_add(state, candidate, transition.candidate_value.total_gain)
            action = (
                BUY
                if option.eligible
                and option.total_advantage > self.thresholds.minimum_purchase_advantage
                else HOLD
            )
            rationale_parts = []
            if slot_neutral:
                rationale_parts.append(
                    "Negative edition is slot-neutral; no incumbent replacement is required"
                )
            rationale_parts.append(
                (
                    f"buy advantage={option.total_advantage:.3f} exceeds "
                    f"threshold={self.thresholds.minimum_purchase_advantage:.3f}"
                )
                if action == BUY
                else (
                    f"buy advantage={option.total_advantage:.3f} does not exceed "
                    f"threshold={self.thresholds.minimum_purchase_advantage:.3f}"
                )
            )
            return JokerAcquisitionDecision(
                action=action,
                candidate=candidate_name,
                selected=option if action == BUY else None,
                options=(option,),
                thresholds=self.thresholds,
                rationale=tuple(rationale_parts),
            )

        options = tuple(
            self._score_replacement(state, candidate, replacement)
            for replacement in transition.alternatives
        )
        ranked = tuple(
            sorted(
                options,
                key=lambda option: (
                    -option.total_advantage,
                    option.replace_index if option.replace_index is not None else 10**9,
                ),
            )
        )
        eligible = [
            option
            for option in ranked
            if option.eligible
            and option.total_advantage
            > self.thresholds.minimum_replacement_advantage
        ]
        if not eligible:
            best = ranked[0] if ranked else None
            best_text = (
                f"{best.total_advantage:.3f}" if best is not None else "none"
            )
            return JokerAcquisitionDecision(
                action=HOLD,
                candidate=candidate_name,
                selected=None,
                options=ranked,
                thresholds=self.thresholds,
                rationale=(
                    f"best replacement advantage={best_text}; threshold="
                    f"{self.thresholds.minimum_replacement_advantage:.3f}",
                ),
            )

        selected = eligible[0]
        return JokerAcquisitionDecision(
            action=REPLACE,
            candidate=candidate_name,
            selected=selected,
            options=ranked,
            thresholds=self.thresholds,
            rationale=(
                f"replace slot {selected.replace_index} {selected.replace_joker}",
                f"replacement advantage={selected.total_advantage:.3f}",
            ),
        )

    def _score_add(
        self,
        state: BalatroState,
        candidate: Joker,
        build_gain: float,
    ) -> JokerAcquisitionOption:
        economics = self._economics(
            state,
            candidate,
            incumbent=None,
            replacement=False,
        )
        eligible = (
            economics.money_after >= 0
            and build_gain > self.thresholds.minimum_purchase_build_gain
        )
        total = build_gain + economics.total_adjustment
        return JokerAcquisitionOption(
            mode=BUY,
            build_gain=build_gain,
            total_advantage=total,
            economics=economics,
            eligible=eligible,
            rationale=(
                f"whole-build gain={build_gain:.3f}",
                f"net spend=${economics.net_spend}",
                f"money after=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
            ),
        )

    def _score_replacement(
        self,
        state: BalatroState,
        candidate: Joker,
        replacement,
    ) -> JokerAcquisitionOption:
        index = int(replacement.replace_index)
        incumbent = state.jokers[index]
        economics = self._economics(
            state,
            candidate,
            incumbent=incumbent,
            replacement=True,
        )
        build_gain = float(replacement.build_delta)
        eligible = (
            economics.money_after >= 0
            and build_gain > self.thresholds.minimum_replacement_build_delta
        )
        total = build_gain + economics.total_adjustment
        return JokerAcquisitionOption(
            mode=REPLACE,
            build_gain=build_gain,
            total_advantage=total,
            economics=economics,
            eligible=eligible,
            replace_index=index,
            replace_joker=type(incumbent).__name__,
            rationale=(
                *replacement.rationale,
                f"sell credit=${economics.sell_credit}",
                f"net spend=${economics.net_spend}",
                f"money after=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
            ),
        )

    def _economics(
        self,
        state: BalatroState,
        candidate: Joker,
        *,
        incumbent: Joker | None,
        replacement: bool,
    ) -> JokerTransactionEconomics:
        price = self._price(candidate)
        sell_credit = self._sell_value(incumbent) if incumbent is not None else 0
        net_spend = price - sell_credit
        money_after = int(state.money) - net_spend

        candidate_edition = self._edition_bonus(candidate)
        incumbent_edition = (
            self._edition_bonus(incumbent) if incumbent is not None else 0.0
        )
        edition_delta = candidate_edition - incumbent_edition

        price_penalty = net_spend * self.thresholds.price_weight
        interest_penalty = (
            self._interest(int(state.money)) - self._interest(money_after)
        ) * self.thresholds.interest_weight
        reserve_penalty = self._incremental_reserve_shortfall(
            int(state.money),
            money_after,
        ) * self.thresholds.reserve_weight
        slot_penalty = (
            0.0
            if replacement or joker_has_negative_edition(candidate)
            else self._slot_penalty_after_add(state)
        )

        return JokerTransactionEconomics(
            price=price,
            sell_credit=sell_credit,
            net_spend=net_spend,
            money_after=money_after,
            edition_delta=edition_delta,
            price_penalty=price_penalty,
            interest_penalty=interest_penalty,
            reserve_penalty=reserve_penalty,
            slot_penalty=slot_penalty,
        )

    def _slot_penalty_after_add(self, state: BalatroState) -> float:
        free_after = int(state.joker_slots) - (len(state.jokers) + 1)
        if free_after <= 0:
            return self.thresholds.last_joker_slot_penalty
        if free_after == 1:
            return self.thresholds.penultimate_joker_slot_penalty
        return 0.0

    def _incremental_reserve_shortfall(self, before: int, after: int) -> int:
        before_shortfall = max(0, int(self.thresholds.reserve_target) - before)
        after_shortfall = max(0, int(self.thresholds.reserve_target) - after)
        return max(0, after_shortfall - before_shortfall)

    @staticmethod
    def _price(item: object) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _sell_value(item: object | None) -> int:
        if item is None:
            return 0
        value = getattr(
            item,
            "sell_cost",
            getattr(item, "sell_value", 0),
        )
        if isinstance(value, dict):
            value = value.get("sell", value.get("value", 0))
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _interest(money: int) -> int:
        return min(5, max(0, int(money)) // 5)

    def _edition_bonus(self, item: object | None) -> float:
        if item is None:
            return 0.0
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
