from __future__ import annotations

"""Final Red/White competence corrections derived from live-run failures.

This layer is intentionally small and semantic. It does not predict hidden shop
contents or draw order. It corrects public-state mistakes observed in live
Red/White runs:

* an empty early scoring engine could reject an affordable direct-scoring Joker
  because reserve economics outweighed the first foothold;
* Paint Brush/Palette could bypass early survival readiness with zero Jokers;
* conditional scoring mechanics discoverable from public rules could be omitted
  from representative shop score projection when their activation context was not
  present in the neutral probe state;
* pace recovery treated a one-card discard too similarly to a multi-card redraw
  even though both consume exactly one discard resource;
* the bounded live planner ranked discard candidates with a separate mini-heuristic,
  bypassing the canonical D1 discard evaluator before expectimax;
* shop Wheel of Fortune was never admitted by the deterministic D4 immediate-use
  path, even with healthy money and eligible editionless Jokers.

The module installs after the existing policy stack so all mechanical/conflict
vetoes remain authoritative and these corrections see the final public decision.
"""

from copy import deepcopy
from dataclasses import replace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
from games.balatro.build.joker_scenarios import (
    ScenarioJokerBehaviorAnalyzer,
    scenario_feature,
)
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.joker_policy import BUY, HOLD, JokerAcquisitionPolicy
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.shop_consumable_policy import (
    BUY_AND_USE,
    HOLD as CONSUMABLE_HOLD,
    ConsumableAcquisitionOption,
    ConsumableAcquisitionPolicy,
)
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy


EARLY_ENGINE_ANTE_LIMIT = 2
FIRST_ENGINE_MINIMUM_CASH_AFTER = 1
FIRST_ENGINE_VOUCHER_RESERVE = 10
EXPENSIVE_HAND_SIZE_VOUCHERS = frozenset({"Paint Brush", "Palette"})
REDRAW_EFFICIENCY_BASE = 8.0
REDRAW_EFFICIENCY_SHORTFALL_WEIGHT = 8.0
WHEEL_NAMES = frozenset({"The Wheel of Fortune", "Wheel of Fortune"})
REPEATED_HAND_SCENARIO = scenario_feature("repeated_hand")


_SCENARIO_ANALYZER = ScenarioJokerBehaviorAnalyzer()


def _ante(state) -> int:
    for name in ("ante", "ante_num"):
        try:
            value = int(getattr(state, name, 0) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def _direct_scoring_candidate(candidate: object) -> bool:
    """Use canonical behavior semantics, not Joker-name allowlists."""
    try:
        descriptor = _SCENARIO_ANALYZER.describe(candidate)
    except (AttributeError, TypeError, ValueError):
        return False
    if descriptor is None:
        return False
    outputs = {
        str(value).lower().replace("_", "")
        for value in set(descriptor.produces) | set(descriptor.transforms)
    }
    return any(
        any(marker in output for marker in ("chips", "mult", "xmult", "score"))
        for output in outputs
    )


def _has_invested_hand(source) -> bool:
    levels = getattr(source, "hand_levels", {}) or {}
    if isinstance(levels, dict):
        values = levels.values()
    else:
        try:
            values = (value for _, value in levels)
        except (TypeError, ValueError):
            return False
    for value in values:
        try:
            if int(value or 0) > 1:
                return True
        except (TypeError, ValueError):
            continue
    return False


def install_red_white_competence_corrections() -> None:
    if getattr(JokerAcquisitionPolicy, "_rw_competence_corrections_installed", False):
        return

    original_joker_decide = JokerAcquisitionPolicy.decide
    original_consumable_decide = ConsumableAcquisitionPolicy.decide
    original_voucher_gate = VoucherAcquisitionPolicy._early_survival_gate
    original_discard_value = LiveHandDecisionEvaluator._discard_value
    original_direct_scoring_gain = JokerBuildValueEvaluator._direct_scoring_gain

    def direct_scoring_gain(self, state, joker):
        base_gain = float(original_direct_scoring_gain(self, state, joker))
        try:
            descriptor = _SCENARIO_ANALYZER.describe(joker)
        except (AttributeError, TypeError, ValueError):
            return base_gain

        # The scenario analyzer already proves when scoring is gated by repeating a
        # hand. B3's neutral score probes previously ignored that public mechanical
        # condition entirely, making mechanics such as Card Sharp look inert in the
        # shop. Evaluate the same literal scorer in both representative states:
        # before the condition and after one same-type hand has been played. This is
        # not a Joker-name bonus and does not fabricate chips/Mult/XMult; it exposes
        # the real modeled effect under its reachable execution context.
        if REPEATED_HAND_SCENARIO not in set(getattr(descriptor, "requires", ()) or ()):
            return base_gain

        repeated_state = deepcopy(state)
        counts = dict(getattr(repeated_state, "round_hand_play_counts", {}) or {})
        for poker_hand, _ in self._scoring_probes(repeated_state):
            counts[poker_hand.value] = max(1, int(counts.get(poker_hand.value, 0) or 0))
        repeated_state.round_hand_play_counts = counts
        repeated_gain = float(original_direct_scoring_gain(self, repeated_state, joker))

        # Representative B3 probes are deliberately equal-weight samples rather
        # than draw probabilities. Preserve that contract by giving the inactive
        # and mechanically active contexts equal representation.
        return (base_gain + repeated_gain) / 2.0

    def joker_decide(self, state, candidate):
        decision = original_joker_decide(self, state, candidate)
        if decision.action != HOLD:
            return decision
        ante = _ante(state)
        if ante < 1 or ante > EARLY_ENGINE_ANTE_LIMIT:
            return decision
        if tuple(getattr(state, "jokers", ()) or ()):
            return decision
        if not _direct_scoring_candidate(candidate):
            return decision

        affordable = [
            option
            for option in tuple(getattr(decision, "options", ()) or ())
            if getattr(option, "mode", None) == BUY
            and int(getattr(getattr(option, "economics", None), "money_after", -1))
            >= FIRST_ENGINE_MINIMUM_CASH_AFTER
        ]
        if not affordable:
            return decision

        raw_selected = max(
            affordable,
            key=lambda option: (
                float(getattr(option, "build_gain", 0.0) or 0.0),
                float(getattr(option, "total_advantage", float("-inf")) or 0.0),
            ),
        )
        selected = replace(raw_selected, eligible=True)
        options = tuple(
            selected if option is raw_selected else option
            for option in tuple(getattr(decision, "options", ()) or ())
        )
        return replace(
            decision,
            action=BUY,
            selected=selected,
            options=options,
            rationale=(
                *tuple(getattr(decision, "rationale", ()) or ()),
                "early first-engine bootstrap: affordable direct-scoring Joker outranks reserve-only HOLD",
                "zero-current-gain scaler admitted because an empty roster has no scoring foothold",
                f"first-engine money after=${selected.economics.money_after}",
                "hidden future shop contents are not predicted",
            ),
        )

    def consumable_decide(self, state, candidate):
        decision = original_consumable_decide(self, state, candidate)
        if decision.action != CONSUMABLE_HOLD:
            return decision
        name = str(getattr(candidate, "name", type(candidate).__name__))
        if name not in WHEEL_NAMES or not isinstance(candidate, Consumable):
            return decision
        if not tuple(getattr(state, "jokers", ()) or ()):
            return decision

        economics = self._economics(state, candidate, occupy_slot=False)
        if economics.money_after < int(self.thresholds.reserve_target):
            return decision
        try:
            can_use = candidate.can_use(ConsumableContext(state=state))
        except (AttributeError, TypeError, ValueError):
            can_use = False
        if not can_use:
            return decision

        expectation = WheelOfFortuneExpectationEvaluator().evaluate(state)
        if not expectation.available or not expectation.complete:
            return decision
        expected_gain = float(expectation.expected_build_gain)
        if expected_gain <= 0.0:
            return decision
        total = expected_gain + economics.total_adjustment
        option = ConsumableAcquisitionOption(
            mode=BUY_AND_USE,
            build_gain=expected_gain,
            immediate_gain=0.0,
            total_advantage=total,
            economics=economics,
            eligible=True,
            executable_action=BalatroAction(BUY_AND_USE_CONSUMABLE, target=candidate),
            rationale=(
                "shop Wheel admitted through the same public-state stochastic edition model used by packs",
                f"analytic expected edition gain={expected_gain:.3f}",
                f"money after purchase=${economics.money_after}",
                "D14 shared money/interest scale remains authoritative against END_SHOP",
                *tuple(expectation.rationale),
            ),
        )
        return replace(
            decision,
            action=BUY_AND_USE,
            selected=option,
            options=(option, *tuple(getattr(decision, "options", ()) or ())),
            rationale=(
                *tuple(getattr(decision, "rationale", ()) or ()),
                "eligible Wheel gets a direct BUY_AND_USE shop mode instead of deterministic-D4 rejection",
            ),
        )

    def voucher_gate(
        state,
        profile,
        label: str,
        *,
        price: int,
        money_after: int,
    ):
        allowed, notes = original_voucher_gate(
            state,
            profile,
            label,
            price=price,
            money_after=money_after,
        )
        if not allowed:
            return allowed, notes

        ante = _ante(state)
        if ante <= 0:
            try:
                ante = int(getattr(profile, "ante", 0) or 0)
            except (TypeError, ValueError):
                ante = 0
        if ante < 1 or ante > EARLY_ENGINE_ANTE_LIMIT:
            return True, notes

        state_jokers = len(tuple(getattr(state, "jokers", ()) or ()))
        profile_jokers = len(tuple(getattr(profile, "joker_names", ()) or ()))
        joker_count = max(state_jokers, profile_jokers)
        invested_hand = _has_invested_hand(state) or _has_invested_hand(profile)

        if (
            joker_count == 0
            and not invested_hand
            and int(money_after) < FIRST_ENGINE_VOUCHER_RESERVE
            and str(label) in EXPENSIVE_HAND_SIZE_VOUCHERS
        ):
            return False, (
                *tuple(notes or ()),
                "D3 first-engine hold: expensive hand-size utility cannot pre-empt the first scoring foothold",
                f"D3 voucher={label} jokers=0 invested_hand=False money_after=${int(money_after)}",
            )
        return True, notes

    def discard_value(self, state, action, context):
        value = float(original_discard_value(self, state, action, context))
        if value <= -1_000_000.0:
            return value

        selected = tuple(getattr(action, "cards", ()) or ())
        redraws = len(selected)
        required = max(1.0, float(getattr(context, "required_per_hand", 1.0) or 1.0))
        best_score = max(0.0, float(getattr(context, "best_play_score", 0.0) or 0.0))
        shortfall = max(0.0, 1.0 - best_score / required)
        if shortfall <= 0.0:
            return value
        if redraws <= 1:
            return value
        if int(getattr(state, "discards_remaining", 0) or 0) <= 1:
            return value

        extra_redraws = min(4, redraws - 1)
        efficiency = extra_redraws * (
            REDRAW_EFFICIENCY_BASE
            + REDRAW_EFFICIENCY_SHORTFALL_WEIGHT * shortfall
        )
        return value + efficiency

    def discard_priority(self, state, action):
        # D1 owns discard desirability. The live expectimax beam must not maintain a
        # second partial scoring system that can prune away the very candidates D1
        # prefers. Card count is only a deterministic tie-break after equal D1 value.
        return float(self.evaluator.evaluate(state, action)), len(action.cards)

    JokerBuildValueEvaluator._direct_scoring_gain = direct_scoring_gain
    JokerAcquisitionPolicy.decide = joker_decide
    ConsumableAcquisitionPolicy.decide = consumable_decide
    VoucherAcquisitionPolicy._early_survival_gate = staticmethod(voucher_gate)
    LiveHandDecisionEvaluator._discard_value = discard_value
    LiveBlindClearPlanner._discard_priority = discard_priority

    JokerBuildValueEvaluator._rw_competence_corrections_installed = True
    JokerAcquisitionPolicy._rw_competence_corrections_installed = True
    ConsumableAcquisitionPolicy._rw_competence_corrections_installed = True
    VoucherAcquisitionPolicy._rw_competence_corrections_installed = True
    LiveHandDecisionEvaluator._rw_competence_corrections_installed = True
    LiveBlindClearPlanner._rw_competence_corrections_installed = True
