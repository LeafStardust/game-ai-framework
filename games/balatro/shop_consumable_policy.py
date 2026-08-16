from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import (
    BUY_AND_USE_CONSUMABLE,
    BUY_CONSUMABLE,
    BalatroAction,
)
from games.balatro.build import ContextualConsumableSynergyEvaluator
from games.balatro.consumable import Consumable
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.state import BalatroState


BUY = "BUY"
BUY_AND_USE = "BUY_AND_USE"
HOLD = "HOLD"


@dataclass(frozen=True)
class ConsumableAcquisitionThresholds:
    """Thresholds owned only by D4 consumable acquisition-mode decisions."""

    minimum_purchase_build_gain: float = 0.0
    minimum_purchase_advantage: float = 0.35
    minimum_buy_and_use_advantage: float = 0.35
    price_weight: float = 0.35
    interest_weight: float = 1.25
    reserve_target: int = 5
    reserve_weight: float = 0.45
    last_consumable_slot_penalty: float = 0.6
    immediate_money_weight: float = 0.20

    def __post_init__(self) -> None:
        nonnegative = (
            "minimum_purchase_build_gain",
            "minimum_purchase_advantage",
            "minimum_buy_and_use_advantage",
            "price_weight",
            "interest_weight",
            "reserve_weight",
            "last_consumable_slot_penalty",
            "immediate_money_weight",
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
    ) -> "ConsumableAcquisitionThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D4 consumable threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class ConsumableTransactionEconomics:
    price: int
    money_after: int
    price_penalty: float
    interest_penalty: float
    reserve_penalty: float
    slot_penalty: float

    @property
    def total_adjustment(self) -> float:
        return -(
            self.price_penalty
            + self.interest_penalty
            + self.reserve_penalty
            + self.slot_penalty
        )


@dataclass(frozen=True)
class ConsumableAcquisitionOption:
    mode: str
    build_gain: float
    immediate_gain: float
    total_advantage: float
    economics: ConsumableTransactionEconomics
    eligible: bool
    executable_action: BalatroAction | None = None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsumableAcquisitionDecision:
    action: str
    candidate: str
    selected: ConsumableAcquisitionOption | None
    options: tuple[ConsumableAcquisitionOption, ...]
    thresholds: ConsumableAcquisitionThresholds
    rationale: tuple[str, ...] = ()


class ConsumableAcquisitionPolicy:
    """D4 HOLD/BUY/BUY_AND_USE policy over public shop state.

    B4 supplies behavior-backed whole-build value and D4 owns only transaction
    economics, consumable-slot opportunity cost, and acquisition thresholds.

    Immediate Buy & Use does not carry a second timing model. D4 simulates the
    deterministic post-purchase state and asks the ordinary held-consumable timing
    policy whether immediate use is admitted. D5/D6/D7 therefore remain the sole
    owners of USE/HOLD and target admission. For now the direct shop transaction is
    deliberately restricted to deterministic no-target economy consumables; target
    transforms, Planets, and stochastic effects remain fail-closed here.
    """

    DETERMINISTIC_BUY_AND_USE_NAMES = frozenset({"The Hermit", "Temperance"})

    def __init__(
        self,
        thresholds: ConsumableAcquisitionThresholds | None = None,
        *,
        evaluator: ContextualConsumableSynergyEvaluator | None = None,
        timing_policy: LiveConsumableTimingPolicy | None = None,
    ) -> None:
        self.thresholds = thresholds or ConsumableAcquisitionThresholds()
        self.evaluator = evaluator or ContextualConsumableSynergyEvaluator()
        self.timing_policy = timing_policy or LiveConsumableTimingPolicy()

    def decide(
        self,
        state: BalatroState,
        candidate: object,
    ) -> ConsumableAcquisitionDecision:
        if state.phase != "SHOP":
            raise ValueError("D4 consumable acquisition requires SHOP phase")

        candidate_name = str(getattr(candidate, "name", type(candidate).__name__))
        if not isinstance(candidate, Consumable):
            return ConsumableAcquisitionDecision(
                action=HOLD,
                candidate=candidate_name,
                selected=None,
                options=(),
                thresholds=self.thresholds,
                rationale=("candidate is not a modeled consumable",),
            )

        evaluation = self.evaluator.evaluate(candidate, state)
        options: list[ConsumableAcquisitionOption] = []
        if len(state.consumables) < int(state.consumable_slots):
            options.append(
                self._score_buy(
                    state,
                    candidate,
                    build_gain=float(evaluation.total_gain),
                    rationale=evaluation.rationale,
                )
            )

        immediate = self._immediate_use_case(state, candidate)
        if immediate is not None:
            immediate_gain, timing_rationale = immediate
            options.append(
                self._score_buy_and_use(
                    state,
                    candidate,
                    build_gain=float(evaluation.total_gain),
                    immediate_gain=immediate_gain,
                    rationale=(*timing_rationale, *evaluation.rationale),
                )
            )

        ranked = tuple(
            sorted(
                options,
                key=lambda option: (
                    -option.total_advantage,
                    0 if option.mode == BUY else 1,
                ),
            )
        )
        eligible = [
            option
            for option in ranked
            if option.eligible
            and (
                option.total_advantage
                > (
                    self.thresholds.minimum_purchase_advantage
                    if option.mode == BUY
                    else self.thresholds.minimum_buy_and_use_advantage
                )
            )
        ]
        if not eligible:
            best = ranked[0] if ranked else None
            best_text = (
                f"{best.mode}={best.total_advantage:.3f}"
                if best is not None
                else "none"
            )
            return ConsumableAcquisitionDecision(
                action=HOLD,
                candidate=candidate_name,
                selected=None,
                options=ranked,
                thresholds=self.thresholds,
                rationale=(
                    f"best D4 option={best_text}; no acquisition mode clears its threshold",
                    f"B4 whole-build gain={evaluation.total_gain:.3f}",
                    *evaluation.rationale,
                ),
            )

        selected = eligible[0]
        return ConsumableAcquisitionDecision(
            action=selected.mode,
            candidate=candidate_name,
            selected=selected,
            options=ranked,
            thresholds=self.thresholds,
            rationale=(
                f"selected D4 mode={selected.mode}",
                f"mode advantage={selected.total_advantage:.3f}",
                *selected.rationale,
            ),
        )

    def _score_buy(
        self,
        state: BalatroState,
        candidate: Consumable,
        *,
        build_gain: float,
        rationale: tuple[str, ...],
    ) -> ConsumableAcquisitionOption:
        economics = self._economics(
            state,
            candidate,
            occupy_slot=True,
        )
        total = build_gain + economics.total_adjustment
        eligible = (
            economics.money_after >= 0
            and build_gain > self.thresholds.minimum_purchase_build_gain
        )
        return ConsumableAcquisitionOption(
            mode=BUY,
            build_gain=build_gain,
            immediate_gain=0.0,
            total_advantage=total,
            economics=economics,
            eligible=eligible,
            executable_action=(
                BalatroAction(BUY_CONSUMABLE, target=candidate)
                if eligible
                else None
            ),
            rationale=(
                f"B4 whole-build gain={build_gain:.3f}",
                f"price=${economics.price}",
                f"money after=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
                *rationale,
            ),
        )

    def _score_buy_and_use(
        self,
        state: BalatroState,
        candidate: Consumable,
        *,
        build_gain: float,
        immediate_gain: float,
        rationale: tuple[str, ...],
    ) -> ConsumableAcquisitionOption:
        economics = self._economics(
            state,
            candidate,
            occupy_slot=False,
        )
        immediate_value = immediate_gain * self.thresholds.immediate_money_weight
        total = build_gain + immediate_value + economics.total_adjustment
        eligible = economics.money_after >= 0 and immediate_gain > 0.0
        return ConsumableAcquisitionOption(
            mode=BUY_AND_USE,
            build_gain=build_gain,
            immediate_gain=immediate_gain,
            total_advantage=total,
            economics=economics,
            eligible=eligible,
            executable_action=(
                BalatroAction(BUY_AND_USE_CONSUMABLE, target=candidate)
                if eligible
                else None
            ),
            rationale=(
                f"B4 whole-build gain={build_gain:.3f}",
                f"D5 admitted deterministic immediate gain=${immediate_gain:g}",
                f"weighted immediate value={immediate_value:.3f}",
                f"price=${economics.price}",
                f"money after purchase=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
                *rationale,
            ),
        )

    def _immediate_use_case(
        self,
        state: BalatroState,
        candidate: Consumable,
    ) -> tuple[float, tuple[str, ...]] | None:
        name = str(getattr(candidate, "name", ""))
        if name not in self.DETERMINISTIC_BUY_AND_USE_NAMES:
            return None

        price = self._price(candidate)
        money_after = int(state.money) - price
        if money_after < 0:
            return None

        simulated = copy.deepcopy(state)
        simulated_candidate = copy.deepcopy(candidate)
        simulated.money = money_after
        simulated.consumables.append(simulated_candidate)

        recommendation = self.timing_policy.recommend(
            simulated,
            simulated_candidate,
        )
        if not recommendation.should_use:
            return None
        if float(recommendation.immediate_gain) <= 0.0:
            return None

        return float(recommendation.immediate_gain), (
            "D4 immediate transaction delegated to post-purchase held-consumable timing",
            *tuple(str(note) for note in recommendation.rationale),
        )

    def _economics(
        self,
        state: BalatroState,
        candidate: Consumable,
        *,
        occupy_slot: bool,
    ) -> ConsumableTransactionEconomics:
        price = self._price(candidate)
        money_after = int(state.money) - price
        price_penalty = price * self.thresholds.price_weight
        interest_penalty = (
            self._interest(int(state.money)) - self._interest(money_after)
        ) * self.thresholds.interest_weight
        reserve_penalty = self._incremental_reserve_shortfall(
            int(state.money),
            money_after,
        ) * self.thresholds.reserve_weight
        slot_penalty = (
            self._slot_penalty_after_buy(state)
            if occupy_slot
            else 0.0
        )
        return ConsumableTransactionEconomics(
            price=price,
            money_after=money_after,
            price_penalty=price_penalty,
            interest_penalty=interest_penalty,
            reserve_penalty=reserve_penalty,
            slot_penalty=slot_penalty,
        )

    def _slot_penalty_after_buy(self, state: BalatroState) -> float:
        free_after = int(state.consumable_slots) - (len(state.consumables) + 1)
        if free_after <= 0:
            return self.thresholds.last_consumable_slot_penalty
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
    def _interest(money: int) -> int:
        return min(5, max(0, int(money)) // 5)
