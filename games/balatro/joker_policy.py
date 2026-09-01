from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.strategy_semantics import StrategyCommitment
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


def _has_current_scoring_foothold(candidate_value: object) -> bool:
    """Return whether D2's literal whole-build probe found current scoring power.

    The early first-Joker relaxation exists to establish a scoring foothold, not
    merely any positive structural/economy axis. ``direct_scoring_gain`` is already
    computed by the canonical Joker build evaluator from public literal score
    projections, so reusing it adds no second scorer or hidden-state inference.
    """
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
            "minimum_purchase_build_gain", "minimum_purchase_advantage",
            "minimum_replacement_build_delta", "minimum_replacement_advantage",
            "aligned_minimum_replacement_advantage", "price_weight", "interest_weight",
            "reserve_weight", "last_joker_slot_penalty", "penultimate_joker_slot_penalty",
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
        return self.edition_delta - self.price_penalty - self.interest_penalty - self.reserve_penalty - self.slot_penalty


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


def _strategy_candidate(composition, strategy_id: str | None):
    if not strategy_id:
        return None
    return next(
        (
            candidate
            for candidate in tuple(getattr(composition, "strategy_candidates", ()) or ())
            if str(getattr(candidate, "strategy_id", "") or "") == str(strategy_id)
        ),
        None,
    )


def _plan_missing_count(plan) -> int:
    if plan is None:
        return 0
    return len(tuple(getattr(plan, "missing_components", ()) or ())) + len(
        tuple(getattr(plan, "missing_features", ()) or ())
    )


def _strategy_transition_bonus(before_comp, after_comp) -> tuple[float, tuple[str, ...]]:
    """Bounded strategy-formation value that stays inside D2's Bond budget.

    Development rank, realization, strategy commitment and Build Health remain
    separate axes. This term therefore rewards only public structural transitions:
    forming a pinned strategy, strengthening/advancing the same pinned strategy,
    resolving explicit plan gaps, or pivoting to a materially stronger pinned plan.
    It does not fabricate direct score and it never bypasses D2 admission/economics.
    """

    before_id = getattr(before_comp, "pinned_strategy_id", None)
    after_id = getattr(after_comp, "pinned_strategy_id", None)
    before_candidate = _strategy_candidate(before_comp, before_id)
    after_candidate = _strategy_candidate(after_comp, after_id)
    before_plan = getattr(before_comp, "strategy_plan", None)
    after_plan = getattr(after_comp, "strategy_plan", None)

    value = 0.0
    notes: list[str] = []

    if before_candidate is None and after_candidate is not None:
        after_commitment = getattr(after_candidate, "commitment", StrategyCommitment.EXPLORATORY)
        if after_commitment >= StrategyCommitment.PINNED:
            value += 1.25
            notes.append(
                f"strategy formed={after_candidate.strategy_id} commitment={after_commitment.name}"
            )

    elif before_candidate is not None and after_candidate is not None:
        before_commitment = getattr(before_candidate, "commitment", StrategyCommitment.EXPLORATORY)
        after_commitment = getattr(after_candidate, "commitment", StrategyCommitment.EXPLORATORY)
        before_strength = float(getattr(before_candidate, "strength", 0.0) or 0.0)
        after_strength = float(getattr(after_candidate, "strength", 0.0) or 0.0)

        if str(after_candidate.strategy_id) == str(before_candidate.strategy_id):
            commitment_gain = max(0, int(after_commitment) - int(before_commitment))
            if commitment_gain:
                commitment_value = min(1.50, 0.75 * commitment_gain)
                value += commitment_value
                notes.append(
                    f"strategy commitment={before_commitment.name}->{after_commitment.name}"
                )

            strength_gain = max(0.0, after_strength - before_strength)
            if strength_gain > 0.0:
                strength_value = min(0.75, 0.15 * strength_gain)
                value += strength_value
                notes.append(
                    f"same-strategy strength={before_strength:.3f}->{after_strength:.3f}"
                )
        else:
            strength_gain = after_strength - before_strength
            if (
                after_commitment >= StrategyCommitment.PINNED
                and strength_gain >= 2.0
            ):
                pivot_value = min(1.25, 0.75 + 0.10 * (strength_gain - 2.0))
                value += pivot_value
                notes.append(
                    "materially stronger pinned pivot="
                    f"{before_candidate.strategy_id}:{before_strength:.3f}->"
                    f"{after_candidate.strategy_id}:{after_strength:.3f}"
                )

    before_plan_id = str(getattr(before_plan, "strategy_id", "") or "")
    after_plan_id = str(getattr(after_plan, "strategy_id", "") or "")
    if before_plan_id and before_plan_id == after_plan_id:
        before_completion = float(getattr(before_plan, "completion", 0.0) or 0.0)
        after_completion = float(getattr(after_plan, "completion", 0.0) or 0.0)
        completion_gain = max(0.0, after_completion - before_completion)
        before_missing = _plan_missing_count(before_plan)
        after_missing = _plan_missing_count(after_plan)
        gaps_filled = max(0, before_missing - after_missing)
        if completion_gain > 0.0 or gaps_filled > 0:
            plan_value = min(1.00, 1.25 * completion_gain + 0.25 * min(2, gaps_filled))
            value += plan_value
            notes.append(
                f"strategy plan progress={before_completion:.3f}->{after_completion:.3f}; "
                f"missing goals={before_missing}->{after_missing}"
            )

    bounded = min(2.50, max(0.0, value))
    if bounded <= 0.0:
        return 0.0, ()
    return bounded, tuple(notes)


def _bond_transition_bonus(
    state: BalatroState,
    candidate: Joker,
    *,
    replace_index: int | None = None,
) -> tuple[float, tuple[str, ...]]:
    """Bounded long-horizon value from canonical Bond/composition transitions.

    Immediate score probes systematically undervalue engines such as Burnt Joker.
    D2 therefore projects only the public one-Joker transition and rewards actual
    Bond development plus canonical strategy formation. All structural authority is
    contained inside the existing four-point Bond-transition budget.
    """
    try:
        before, before_comp = evaluate_bond_composition(state)
        projected = copy.copy(state)
        projected.jokers = list(getattr(state, "jokers", ()) or ())
        if replace_index is None:
            projected.jokers.append(candidate)
        else:
            if replace_index < 0 or replace_index >= len(projected.jokers):
                return 0.0, ()
            projected.jokers[replace_index] = candidate
        after, after_comp = evaluate_bond_composition(projected)
    except (AttributeError, TypeError, ValueError):
        return 0.0, ()

    before_by_id = {d.bond_id: d for d in before}
    established_before = {
        development.bond_id
        for development in before
        if int(getattr(development, "rank", BondRank.LOCKED)) >= int(BondRank.R1)
    }
    established_rank_gain = 0.0
    new_rank_gain = 0.0
    progress_gain = 0.0
    improved = []
    for development in after:
        previous = before_by_id.get(development.bond_id)
        raw_old_rank = (
            int(getattr(previous, "rank", BondRank.LOCKED))
            if previous is not None
            else int(BondRank.LOCKED)
        )
        old_rank = max(0, raw_old_rank)
        new_rank = int(getattr(development, "rank", BondRank.LOCKED))
        if new_rank > old_rank:
            gain = float(new_rank - old_rank)
            if old_rank >= int(BondRank.R1):
                established_rank_gain += gain
            else:
                new_rank_gain += gain
            improved.append(
                f"{development.bond_id}:"
                f"{BondRank(raw_old_rank).name if raw_old_rank in range(-1, 6) else raw_old_rank}"
                f"->{development.rank.name}"
            )
        old_contribution = (
            float(getattr(previous, "contribution", 0.0) or 0.0)
            if previous is not None
            else 0.0
        )
        delta = max(
            0.0,
            float(getattr(development, "contribution", 0.0) or 0.0) - old_contribution,
        )
        threshold = float(getattr(development, "next_rank_threshold", 0.0) or 0.0)
        if old_rank >= int(BondRank.R1) and delta > 0.0 and threshold > 0.0:
            progress_gain += min(1.0, delta / threshold)

    coherence_delta = max(
        0.0,
        float(getattr(after_comp, "coherence_score", 0.0) or 0.0)
        - float(getattr(before_comp, "coherence_score", 0.0) or 0.0),
    )
    strategy_value, strategy_notes = _strategy_transition_bonus(before_comp, after_comp)

    before_synergies = set(tuple(value) for value in getattr(before_comp, "synergies", ()) or ())
    after_synergies = set(tuple(value) for value in getattr(after_comp, "synergies", ()) or ())
    new_synergies = after_synergies.difference(before_synergies)
    # A single newly acquired component may contribute to multiple Bond labels.
    # Do not reward those labels for being "synergistic" with each other unless the
    # purchase actually connects to an axis that existed before the transaction.
    # This keeps structural reward for genuine reinforcement (Erosion -> Trading
    # Card) while preventing Trading Card alone from manufacturing its own synergy.
    reinforcing_synergies = {
        pair for pair in new_synergies if established_before.intersection(pair)
    }
    synergy_gain = len(reinforcing_synergies)
    suppressed_self_synergies = len(new_synergies) - synergy_gain

    before_motifs = {
        str(motif.motif_id): motif
        for motif in tuple(getattr(before_comp, "motifs", ()) or ())
    }
    motif_gain = 0.0
    for motif in tuple(getattr(after_comp, "motifs", ()) or ()):
        previous = before_motifs.get(str(motif.motif_id))
        old_state = int(getattr(previous, "state", 0) or 0) if previous is not None else 0
        new_state = int(getattr(motif, "state", 0) or 0)
        state_gain = max(0, new_state - old_state)
        old_missing = len(tuple(getattr(previous, "missing_components", ()) or ())) if previous is not None else len(tuple(getattr(motif, "missing_components", ()) or ())) + 1
        new_missing = len(tuple(getattr(motif, "missing_components", ()) or ()))
        motif_gain += float(state_gain) + 0.5 * max(0, old_missing - new_missing)

    before_conflicts = {
        frozenset(str(bond_id) for bond_id in pair)
        for pair in tuple(getattr(before_comp, "conflicts", ()) or ())
    }
    after_conflicts = {
        frozenset(str(bond_id) for bond_id in pair)
        for pair in tuple(getattr(after_comp, "conflicts", ()) or ())
    }
    selected_before = set(str(bond_id) for bond_id in tuple(getattr(before_comp, "bond_ids", ()) or ()))
    new_conflicts = after_conflicts.difference(before_conflicts)
    conflicts_with_selected = tuple(
        sorted(tuple(sorted(pair)))
        for pair in new_conflicts
        if selected_before.intersection(pair)
    )

    before_pinned = _strategy_candidate(before_comp, getattr(before_comp, "pinned_strategy_id", None))
    after_pinned = _strategy_candidate(after_comp, getattr(after_comp, "pinned_strategy_id", None))
    materially_stronger_pinned_pivot = False
    if before_pinned is not None and after_pinned is not None:
        before_strength = float(getattr(before_pinned, "strength", 0.0) or 0.0)
        after_strength = float(getattr(after_pinned, "strength", 0.0) or 0.0)
        materially_stronger_pinned_pivot = bool(
            str(getattr(before_pinned, "strategy_id", ""))
            != str(getattr(after_pinned, "strategy_id", ""))
            and getattr(after_pinned, "commitment", StrategyCommitment.EXPLORATORY)
            >= StrategyCommitment.PINNED
            and after_strength - before_strength >= 2.0
        )
    conflicting_transition = bool(conflicts_with_selected) and not materially_stronger_pinned_pivot

    has_existing_engine = bool(established_before)
    aligned = bool(
        not conflicting_transition
        and (
            established_rank_gain > 0.0
            or synergy_gain > 0
            or motif_gain > 0.0
            or strategy_value > 0.0
        )
    )

    if conflicting_transition:
        conflict_weight = max(
            1.0,
            established_rank_gain + new_rank_gain + min(1.0, progress_gain),
        )
        adjustment = -min(1.50, 0.75 * conflict_weight)
    elif aligned:
        adjustment = min(
            4.0,
            1.75 * (established_rank_gain + new_rank_gain)
            + 0.50 * min(1.0, progress_gain)
            + 0.50 * min(2, synergy_gain)
            + 0.75 * min(2.0, motif_gain)
            + strategy_value,
        )
    elif new_rank_gain > 0.0 and not has_existing_engine:
        adjustment = min(0.50, 0.50 * new_rank_gain)
    elif new_rank_gain > 0.0:
        adjustment = -min(1.50, 0.75 * new_rank_gain)
    else:
        adjustment = min(0.50, 0.35 * min(1.0, progress_gain))

    if abs(adjustment) <= 1e-12:
        return 0.0, ()
    return adjustment, (
        f"canonical Bond transition adjustment={adjustment:+.3f}",
        f"established rank gain={established_rank_gain:.1f}; new-axis rank gain={new_rank_gain:.1f}; "
        f"progress gain={progress_gain:.3f}; synergy gain={synergy_gain}; motif gain={motif_gain:.3f}; "
        f"coherence delta={coherence_delta:.3f}; strategy value={strategy_value:.3f}",
        *((f"suppressed same-purchase synergy count={suppressed_self_synergies}",) if suppressed_self_synergies else ()),
        *(("Bond rank transitions=" + ", ".join(improved),) if improved else ()),
        *(("new conflicts with selected composition=" + ", ".join("/".join(pair) for pair in conflicts_with_selected),) if conflicts_with_selected else ()),
        *strategy_notes,
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

            rationale_parts = []
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
        bond_bonus, bond_notes = _bond_transition_bonus(state, candidate)
        build_gain = float(build_gain) + bond_bonus
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
                f"whole-build gain including Bond projection={build_gain:.3f}",
                *bond_notes,
                f"net spend=${economics.net_spend}",
                f"money after=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
            ),
        )

    def _score_replacement(self, state: BalatroState, candidate: Joker, replacement) -> JokerAcquisitionOption:
        index = int(replacement.replace_index)
        incumbent = state.jokers[index]
        economics = self._economics(state, candidate, incumbent=incumbent, replacement=True)
        bond_bonus, bond_notes = _bond_transition_bonus(state, candidate, replace_index=index)
        raw_build_delta = float(replacement.build_delta)
        build_gain = raw_build_delta + bond_bonus
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
                *bond_notes,
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
