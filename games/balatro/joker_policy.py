from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.bonds.strategy_delta import strategy_delta_from_states
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker import Joker
from games.balatro.joker_edition import (
    EDITION_UNIVERSAL_VALUES,
    joker_edition_universal_value,
    joker_has_negative_edition,
)
from games.balatro.state import BalatroState


BUY = "BUY"
REPLACE = "REPLACE"
HOLD = "HOLD"

_EARLY_ENGINE_ANTE_LIMIT = 2
_FIRST_ENGINE_MINIMUM_CASH_AFTER = 2
# Initial integration calibration only. Live tuning belongs to Phase L.
_JOKER_STRATEGY_WEIGHT = 0.10


def _has_current_scoring_foothold(candidate_value: object) -> bool:
    """Return whether D2's literal whole-build probe found current scoring power."""
    try:
        return float(getattr(candidate_value, "direct_scoring_gain", 0.0) or 0.0) > 0.0
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class JokerAcquisitionThresholds:
    """Thresholds owned only by D2 Joker acquisition/replacement decisions."""

    minimum_purchase_build_gain: float = 0.0
    minimum_purchase_advantage: float = 0.35
    minimum_replacement_build_delta: float = 0.0
    minimum_replacement_advantage: float = 0.75
    aligned_minimum_replacement_advantage: float = 0.25
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
            "aligned_minimum_replacement_advantage",
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
    def from_mapping(cls, value: Mapping[str, object] | None) -> "JokerAcquisitionThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError("unknown D2 Joker threshold(s): " + ", ".join(unknown))
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


def _project_joker_transition(
    state: BalatroState,
    candidate: Joker,
    *,
    replace_index: int | None = None,
) -> BalatroState:
    """Project only the public persistent Joker ownership transition.

    Mechanical score/economy projection remains owned by D2's existing build
    planner. This projector exists solely so canonical StrategyDelta can compare
    the resulting persistent build state.
    """
    copy_method = getattr(state, "copy", None)
    projected = copy_method() if callable(copy_method) else copy.copy(state)
    projected.jokers = list(getattr(state, "jokers", ()) or ())
    if replace_index is None:
        projected.jokers.append(candidate)
    else:
        if replace_index < 0 or replace_index >= len(projected.jokers):
            raise IndexError("replacement Joker index out of range")
        projected.jokers[replace_index] = candidate
    return projected


def _bond_transition_bonus(
    state: BalatroState,
    candidate: Joker,
    *,
    replace_index: int | None = None,
) -> tuple[float, tuple[str, ...]]:
    """Compatibility name for the canonical whole-build StrategyDelta term.

    The former implementation separately rewarded Bond ranks, coherence,
    pinned strategies, StrategyPlan progress, legacy motifs, and pivot state.
    Phase H replaces that parallel authority with exactly one projected
    BuildValue comparison. The name remains temporarily to avoid widening this
    migration slice; its semantics are now entirely canonical.
    """
    try:
        projected = _project_joker_transition(
            state,
            candidate,
            replace_index=replace_index,
        )
        delta = strategy_delta_from_states(state, projected)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return 0.0, ()

    weighted = _JOKER_STRATEGY_WEIGHT * float(delta.value)
    if abs(weighted) <= 1e-12:
        return 0.0, ()
    return weighted, (
        f"canonical StrategyDelta={delta.value:+.3f}",
        f"raw BuildValue delta={delta.raw_delta:+.3f}",
        f"transition inertia={delta.transition_cost:.3f}",
        f"Joker strategy weight={_JOKER_STRATEGY_WEIGHT:.3f}",
        f"weighted strategic adjustment={weighted:+.3f}",
    )


class JokerAcquisitionPolicy:
    """D2 build-aware Joker buy/replace decision with explicit HOLD baseline."""

    EDITION_BONUSES = EDITION_UNIVERSAL_VALUES

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

    def decide(self, state: BalatroState, candidate: object) -> JokerAcquisitionDecision:
        candidate_name = type(candidate).__name__
        if not isinstance(candidate, Joker):
            return JokerAcquisitionDecision(
                HOLD,
                candidate_name,
                None,
                (),
                self.thresholds,
                ("candidate is not a modeled Joker",),
            )

        transition = self.transition_planner.plan(state, candidate)
        slot_neutral = joker_has_negative_edition(candidate)
        if len(state.jokers) < int(state.joker_slots) or slot_neutral:
            strategic_conflict = bool(
                getattr(transition.candidate_value, "applicability", None) == "CONFLICT"
            )
            option = self._score_add(
                state,
                candidate,
                transition.candidate_value.total_gain,
                strategic_conflict=strategic_conflict,
            )
            action = (
                BUY
                if option.eligible
                and option.total_advantage > self.thresholds.minimum_purchase_advantage
                else HOLD
            )
            try:
                ante = int(getattr(state, "ante", getattr(state, "ante_num", 0)) or 0)
            except (TypeError, ValueError):
                ante = 0
            first_joker_early = (
                1 <= ante <= _EARLY_ENGINE_ANTE_LIMIT
                and not tuple(getattr(state, "jokers", ()) or ())
            )
            first_joker_cash_safe = (
                not first_joker_early
                or int(option.economics.money_after) >= _FIRST_ENGINE_MINIMUM_CASH_AFTER
            )
            if action == BUY and not first_joker_cash_safe:
                action = HOLD
            first_engine_bootstrap = (
                action == HOLD
                and option.eligible
                and first_joker_early
                and float(option.build_gain) > 0.0
                and _has_current_scoring_foothold(transition.candidate_value)
                and first_joker_cash_safe
            )
            if first_engine_bootstrap:
                action = BUY

            rationale_parts: list[str] = []
            if slot_neutral:
                rationale_parts.append(
                    "Negative edition is slot-neutral; no incumbent replacement is required"
                )
            if first_joker_early and not first_joker_cash_safe:
                rationale_parts.append(
                    f"early first-Joker purchase would leave ${option.economics.money_after}; "
                    f"minimum runway is ${_FIRST_ENGINE_MINIMUM_CASH_AFTER}"
                )
            elif first_engine_bootstrap:
                rationale_parts.extend(
                    (
                        "early first-engine bootstrap: positive current scoring gain can outrank reserve-only HOLD",
                        f"mechanically grounded build gain={option.build_gain:.3f}",
                        f"literal direct scoring gain={float(getattr(transition.candidate_value, 'direct_scoring_gain', 0.0) or 0.0):.6f}",
                        f"first-engine money after=${option.economics.money_after}",
                        "strategic conflicts remain ineligible",
                        "hidden future shop contents are not predicted",
                    )
                )
            else:
                rationale_parts.append(
                    f"buy advantage={option.total_advantage:.3f} "
                    f"{'exceeds' if action == BUY else 'does not exceed'} "
                    f"threshold={self.thresholds.minimum_purchase_advantage:.3f}"
                )
            return JokerAcquisitionDecision(
                action,
                candidate_name,
                option if action == BUY else None,
                (option,),
                self.thresholds,
                tuple(rationale_parts),
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
        replacement_advantage_threshold = self.thresholds.minimum_replacement_advantage
        eligible = [
            option
            for option in ranked
            if option.eligible
            and option.total_advantage > replacement_advantage_threshold
        ]
        if not eligible:
            best = ranked[0] if ranked else None
            return JokerAcquisitionDecision(
                HOLD,
                candidate_name,
                None,
                ranked,
                self.thresholds,
                (
                    f"best replacement advantage={best.total_advantage:.3f}"
                    if best
                    else "best replacement advantage=none",
                    f"replacement threshold={replacement_advantage_threshold:.3f}",
                ),
            )
        selected = eligible[0]
        return JokerAcquisitionDecision(
            REPLACE,
            candidate_name,
            selected,
            ranked,
            self.thresholds,
            (
                f"replace slot {selected.replace_index} {selected.replace_joker}",
                f"replacement advantage={selected.total_advantage:.3f}",
                f"replacement threshold={replacement_advantage_threshold:.3f}",
            ),
        )

    def _score_add(
        self,
        state: BalatroState,
        candidate: Joker,
        build_gain: float,
        *,
        strategic_conflict: bool = False,
    ) -> JokerAcquisitionOption:
        strategy_adjustment, strategy_notes = _bond_transition_bonus(state, candidate)
        build_gain = float(build_gain) + strategy_adjustment
        economics = self._economics(state, candidate, incumbent=None, replacement=False)
        eligible = (
            economics.money_after >= 0
            and not strategic_conflict
            and (
                build_gain > self.thresholds.minimum_purchase_build_gain
                or joker_edition_universal_value(candidate) > 0.0
            )
        )
        total = build_gain + economics.total_adjustment
        return JokerAcquisitionOption(
            BUY,
            build_gain,
            total,
            economics,
            eligible,
            rationale=(
                f"whole-build gain including StrategyDelta={build_gain:.3f}",
                *strategy_notes,
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
        economics = self._economics(state, candidate, incumbent=incumbent, replacement=True)
        strategy_adjustment, strategy_notes = _bond_transition_bonus(
            state,
            candidate,
            replace_index=index,
        )
        raw_build_delta = float(replacement.build_delta)
        build_gain = raw_build_delta + strategy_adjustment
        eligible = (
            bool(getattr(replacement, "eligible", True))
            and getattr(replacement, "blocked_reason", None) is None
            and economics.money_after >= 0
            and raw_build_delta > self.thresholds.minimum_replacement_build_delta
            and build_gain > self.thresholds.minimum_replacement_build_delta
        )
        total = build_gain + economics.total_adjustment
        return JokerAcquisitionOption(
            REPLACE,
            build_gain,
            total,
            economics,
            eligible,
            replace_index=index,
            replace_joker=type(incumbent).__name__,
            rationale=(
                *replacement.rationale,
                f"raw whole-build replacement delta={raw_build_delta:.3f}",
                *strategy_notes,
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
        incumbent_edition = self._edition_bonus(incumbent) if incumbent is not None else 0.0
        edition_delta = candidate_edition - incumbent_edition
        price_penalty = net_spend * self.thresholds.price_weight
        interest_penalty = (
            self._interest(int(state.money)) - self._interest(money_after)
        ) * self.thresholds.interest_weight
        reserve_penalty = self._incremental_reserve_shortfall(
            int(state.money), money_after
        ) * self.thresholds.reserve_weight
        slot_penalty = (
            0.0
            if replacement or joker_has_negative_edition(candidate)
            else self._slot_penalty_after_add(state)
        )
        return JokerTransactionEconomics(
            price,
            sell_credit,
            net_spend,
            money_after,
            edition_delta,
            price_penalty,
            interest_penalty,
            reserve_penalty,
            slot_penalty,
        )

    def _slot_penalty_after_add(self, state: BalatroState) -> float:
        free_after = int(state.joker_slots) - (len(state.jokers) + 1)
        if free_after <= 0:
            return self.thresholds.last_joker_slot_penalty
        if free_after == 1:
            return self.thresholds.penultimate_joker_slot_penalty
        return 0.0

    def _incremental_reserve_shortfall(self, before: int, after: int) -> int:
        return max(
            0,
            max(0, int(self.thresholds.reserve_target) - after)
            - max(0, int(self.thresholds.reserve_target) - before),
        )

    @staticmethod
    def _price(item: object) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        value = value.get("buy", 0) if isinstance(value, dict) else value
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _sell_value(item: object | None) -> int:
        if item is None:
            return 0
        value = getattr(item, "sell_cost", getattr(item, "sell_value", 0))
        value = value.get("sell", value.get("value", 0)) if isinstance(value, dict) else value
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _interest(money: int) -> int:
        return min(5, max(0, int(money)) // 5)

    def _edition_bonus(self, item: object | None) -> float:
        return joker_edition_universal_value(item)
