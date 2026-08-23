from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
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
            "minimum_purchase_build_gain", "minimum_purchase_advantage",
            "minimum_replacement_build_delta", "minimum_replacement_advantage",
            "aligned_minimum_replacement_advantage", "price_weight", "interest_weight",
            "reserve_weight", "last_joker_slot_penalty", "penultimate_joker_slot_penalty",
        )
        for name in nonnegative:
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")
        if int(self.reserve_target) < 0: raise ValueError("reserve_target cannot be negative")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object] | None) -> "JokerAcquisitionThresholds":
        if not value: return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown: raise ValueError("unknown D2 Joker threshold(s): " + ", ".join(unknown))
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class JokerTransactionEconomics:
    price: int; sell_credit: int; net_spend: int; money_after: int
    edition_delta: float; price_penalty: float; interest_penalty: float; reserve_penalty: float; slot_penalty: float
    @property
    def total_adjustment(self) -> float:
        return self.edition_delta - self.price_penalty - self.interest_penalty - self.reserve_penalty - self.slot_penalty


@dataclass(frozen=True)
class JokerAcquisitionOption:
    mode: str; build_gain: float; total_advantage: float; economics: JokerTransactionEconomics; eligible: bool
    replace_index: int | None = None; replace_joker: str | None = None; rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class JokerAcquisitionDecision:
    action: str; candidate: str; selected: JokerAcquisitionOption | None; options: tuple[JokerAcquisitionOption, ...]
    thresholds: JokerAcquisitionThresholds; rationale: tuple[str, ...] = ()


def _bond_transition_bonus(state: BalatroState, candidate: Joker, *, replace_index: int | None = None) -> tuple[float, tuple[str, ...]]:
    """Bounded long-horizon value from the canonical Bond composition.

    Immediate score probes systematically undervalue engines such as Burnt Joker.
    D2 therefore projects only the public one-Joker transition and rewards actual
    Bond rank/progress gains. This does not inspect future shops, draws, or RNG.
    """
    try:
        before, before_comp = evaluate_bond_composition(state)
        projected = copy.copy(state)
        projected.jokers = list(getattr(state, "jokers", ()) or ())
        if replace_index is None:
            projected.jokers.append(candidate)
        else:
            if replace_index < 0 or replace_index >= len(projected.jokers): return 0.0, ()
            projected.jokers[replace_index] = candidate
        after, after_comp = evaluate_bond_composition(projected)
    except (AttributeError, TypeError, ValueError):
        return 0.0, ()

    before_by_id = {d.bond_id: d for d in before}
    rank_gain = 0.0; progress_gain = 0.0; improved = []
    for development in after:
        previous = before_by_id.get(development.bond_id)
        old_rank = int(getattr(previous, "rank", BondRank.LOCKED)) if previous is not None else 0
        new_rank = int(getattr(development, "rank", BondRank.LOCKED))
        if new_rank > old_rank:
            rank_gain += float(new_rank - old_rank)
            improved.append(f"{development.bond_id}:{BondRank(old_rank).name if old_rank in range(0,6) else old_rank}->{development.rank.name}")
        old_contribution = float(getattr(previous, "contribution", 0.0) or 0.0) if previous is not None else 0.0
        delta = max(0.0, float(getattr(development, "contribution", 0.0) or 0.0) - old_contribution)
        threshold = float(getattr(development, "next_rank_threshold", 0.0) or 0.0)
        if delta > 0.0 and threshold > 0.0:
            progress_gain += min(1.0, delta / threshold)

    coherence_delta = max(0.0, float(getattr(after_comp, "coherence_score", 0.0) or 0.0) - float(getattr(before_comp, "coherence_score", 0.0) or 0.0))
    # A real rank gain is worth materially more than ordinary contextual noise;
    # progress without a rank is useful but bounded. Maximum authority remains 4.
    bonus = min(4.0, 2.75 * rank_gain + 0.75 * min(1.0, progress_gain) + 0.10 * min(5.0, coherence_delta))
    if bonus <= 0.0: return 0.0, ()
    return bonus, (
        f"canonical Bond transition bonus={bonus:.3f}",
        f"Bond rank gain={rank_gain:.1f}; progress gain={progress_gain:.3f}; coherence delta={coherence_delta:.3f}",
        *(('Bond rank transitions=' + ', '.join(improved),) if improved else ()),
    )


class JokerAcquisitionPolicy:
    """D2 build-aware Joker buy/replace decision with explicit HOLD baseline."""
    EDITION_BONUSES = EDITION_UNIVERSAL_VALUES

    def __init__(self, thresholds: JokerAcquisitionThresholds | None = None, *, transition_planner: JokerBuildTransitionPlanner | None = None) -> None:
        self.thresholds = thresholds or JokerAcquisitionThresholds()
        self.transition_planner = transition_planner or JokerBuildTransitionPlanner(minimum_add_gain=0.0, minimum_replacement_delta=0.0)

    def decide(self, state: BalatroState, candidate: object) -> JokerAcquisitionDecision:
        candidate_name = type(candidate).__name__
        if not isinstance(candidate, Joker):
            return JokerAcquisitionDecision(HOLD, candidate_name, None, (), self.thresholds, ("candidate is not a modeled Joker",))
        transition = self.transition_planner.plan(state, candidate)
        slot_neutral = joker_has_negative_edition(candidate)
        if len(state.jokers) < int(state.joker_slots) or slot_neutral:
            strategic_conflict = bool(getattr(transition.candidate_value, "applicability", None) == "CONFLICT")
            option = self._score_add(state, candidate, transition.candidate_value.total_gain, strategic_conflict=strategic_conflict)
            action = BUY if option.eligible and option.total_advantage > self.thresholds.minimum_purchase_advantage else HOLD
            rationale_parts = []
            if slot_neutral: rationale_parts.append("Negative edition is slot-neutral; no incumbent replacement is required")
            rationale_parts.append(f"buy advantage={option.total_advantage:.3f} {'exceeds' if action == BUY else 'does not exceed'} threshold={self.thresholds.minimum_purchase_advantage:.3f}")
            return JokerAcquisitionDecision(action, candidate_name, option if action == BUY else None, (option,), self.thresholds, tuple(rationale_parts))

        options = tuple(self._score_replacement(state, candidate, replacement) for replacement in transition.alternatives)
        ranked = tuple(sorted(options, key=lambda option: (-option.total_advantage, option.replace_index if option.replace_index is not None else 10**9)))
        # Canonical Bond value is already included in each option's build gain. No
        # categorical Gold/Silver/Bronze shortcut remains in D2.
        replacement_advantage_threshold = self.thresholds.minimum_replacement_advantage
        eligible = [o for o in ranked if o.eligible and o.total_advantage > replacement_advantage_threshold]
        if not eligible:
            best = ranked[0] if ranked else None
            return JokerAcquisitionDecision(HOLD, candidate_name, None, ranked, self.thresholds,
                (f"best replacement advantage={best.total_advantage:.3f}" if best else "best replacement advantage=none", f"replacement threshold={replacement_advantage_threshold:.3f}"))
        selected = eligible[0]
        return JokerAcquisitionDecision(REPLACE, candidate_name, selected, ranked, self.thresholds,
            (f"replace slot {selected.replace_index} {selected.replace_joker}", f"replacement advantage={selected.total_advantage:.3f}", f"replacement threshold={replacement_advantage_threshold:.3f}"))

    def _score_add(self, state: BalatroState, candidate: Joker, build_gain: float, *, strategic_conflict: bool = False) -> JokerAcquisitionOption:
        bond_bonus, bond_notes = _bond_transition_bonus(state, candidate)
        build_gain = float(build_gain) + bond_bonus
        economics = self._economics(state, candidate, incumbent=None, replacement=False)
        eligible = economics.money_after >= 0 and not strategic_conflict and (build_gain > self.thresholds.minimum_purchase_build_gain or joker_edition_universal_value(candidate) > 0.0)
        total = build_gain + economics.total_adjustment
        return JokerAcquisitionOption(BUY, build_gain, total, economics, eligible, rationale=(f"whole-build gain including Bond projection={build_gain:.3f}", *bond_notes, f"net spend=${economics.net_spend}", f"money after=${economics.money_after}", f"economic adjustment={economics.total_adjustment:.3f}"))

    def _score_replacement(self, state: BalatroState, candidate: Joker, replacement) -> JokerAcquisitionOption:
        index = int(replacement.replace_index); incumbent = state.jokers[index]
        economics = self._economics(state, candidate, incumbent=incumbent, replacement=True)
        bond_bonus, bond_notes = _bond_transition_bonus(state, candidate, replace_index=index)
        build_gain = float(replacement.build_delta) + bond_bonus
        eligible = bool(getattr(replacement, "eligible", True)) and getattr(replacement, "blocked_reason", None) is None and economics.money_after >= 0 and build_gain > self.thresholds.minimum_replacement_build_delta
        total = build_gain + economics.total_adjustment
        return JokerAcquisitionOption(REPLACE, build_gain, total, economics, eligible, replace_index=index, replace_joker=type(incumbent).__name__, rationale=(*replacement.rationale, *bond_notes, f"sell credit=${economics.sell_credit}", f"net spend=${economics.net_spend}", f"money after=${economics.money_after}", f"economic adjustment={economics.total_adjustment:.3f}"))

    def _economics(self, state: BalatroState, candidate: Joker, *, incumbent: Joker | None, replacement: bool) -> JokerTransactionEconomics:
        price = self._price(candidate); sell_credit = self._sell_value(incumbent) if incumbent is not None else 0
        net_spend = price - sell_credit; money_after = int(state.money) - net_spend
        candidate_edition = self._edition_bonus(candidate); incumbent_edition = self._edition_bonus(incumbent) if incumbent is not None else 0.0
        edition_delta = candidate_edition - incumbent_edition
        price_penalty = net_spend * self.thresholds.price_weight
        interest_penalty = (self._interest(int(state.money)) - self._interest(money_after)) * self.thresholds.interest_weight
        reserve_penalty = self._incremental_reserve_shortfall(int(state.money), money_after) * self.thresholds.reserve_weight
        slot_penalty = 0.0 if replacement or joker_has_negative_edition(candidate) else self._slot_penalty_after_add(state)
        return JokerTransactionEconomics(price, sell_credit, net_spend, money_after, edition_delta, price_penalty, interest_penalty, reserve_penalty, slot_penalty)

    def _slot_penalty_after_add(self, state: BalatroState) -> float:
        free_after = int(state.joker_slots) - (len(state.jokers) + 1)
        if free_after <= 0: return self.thresholds.last_joker_slot_penalty
        if free_after == 1: return self.thresholds.penultimate_joker_slot_penalty
        return 0.0

    def _incremental_reserve_shortfall(self, before: int, after: int) -> int:
        return max(0, max(0, int(self.thresholds.reserve_target) - after) - max(0, int(self.thresholds.reserve_target) - before))

    @staticmethod
    def _price(item: object) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0)); value = value.get("buy", 0) if isinstance(value, dict) else value
        try: return max(0, int(value))
        except (TypeError, ValueError): return 0

    @staticmethod
    def _sell_value(item: object | None) -> int:
        if item is None: return 0
        value = getattr(item, "sell_cost", getattr(item, "sell_value", 0)); value = value.get("sell", value.get("value", 0)) if isinstance(value, dict) else value
        try: return max(0, int(value))
        except (TypeError, ValueError): return 0

    @staticmethod
    def _interest(money: int) -> int: return min(5, max(0, int(money)) // 5)

    def _edition_bonus(self, item: object | None) -> float: return joker_edition_universal_value(item)
