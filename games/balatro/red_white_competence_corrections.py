from __future__ import annotations

"""Final Red/White competence corrections derived from live-run failures.

This layer is intentionally small and semantic. It does not predict hidden shop
contents or draw order. It corrects public-state mistakes observed in live
Red/White runs:

* an empty early scoring engine could reject an affordable, mechanically positive
  Joker because reserve economics outweighed the first foothold;
* Paint Brush/Palette could bypass early survival readiness with zero Jokers;
* conditional scoring mechanics discoverable from public rules could be omitted
  from representative shop score projection when their activation context was not
  present in the neutral probe state;
* shop Wheel of Fortune was never admitted by the deterministic D4 immediate-use
  path, even with healthy money and eligible editionless Jokers.

D1 multi-card redraw efficiency and discard-beam ranking now live in the canonical
D1 evaluator/planner path. Visible two-Joker Bond planning now lives directly in
D14. This module remains installed only for the still-unconsolidated family-local
shop/build corrections below.
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
from games.balatro.celestial_shop_headroom_fast_path import (
    install_celestial_shop_headroom_fast_path,
)
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.joker_policy import BUY, HOLD, JokerAcquisitionPolicy
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
    install_celestial_shop_headroom_fast_path()
    if getattr(JokerAcquisitionPolicy, "_rw_competence_corrections_installed", False):
        return

    original_joker_decide = JokerAcquisitionPolicy.decide
    original_consumable_decide = ConsumableAcquisitionPolicy.decide
    original_voucher_gate = VoucherAcquisitionPolicy._early_survival_gate
    original_direct_scoring_gain = JokerBuildValueEvaluator._direct_scoring_gain

    def direct_scoring_gain(self, state, joker):
        base_gain = float(original_direct_scoring_gain(self, state, joker))
        try:
            descriptor = _SCENARIO_ANALYZER.describe(joker)
        except (AttributeError, TypeError, ValueError):
            return base_gain

        if REPEATED_HAND_SCENARIO not in set(getattr(descriptor, "requires", ()) or ()):
            return base_gain

        repeated_state = deepcopy(state)
        counts = dict(getattr(repeated_state, "round_hand_play_counts", {}) or {})
        for poker_hand, _ in self._scoring_probes(repeated_state):
            counts[poker_hand.value] = max(1, int(counts.get(poker_hand.value, 0) or 0))
        repeated_state.round_hand_play_counts = counts
        repeated_gain = float(original_direct_scoring_gain(self, repeated_state, joker))
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

        affordable = [
            option
            for option in tuple(getattr(decision, "options", ()) or ())
            if getattr(option, "mode", None) == BUY
            and float(getattr(option, "build_gain", 0.0) or 0.0) > 0.0
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
                "early first-engine bootstrap: positive literal/contextual D2 build gain can outrank reserve-only HOLD",
                f"mechanically grounded build gain={selected.build_gain:.3f}",
                f"first-engine money after=${selected.economics.money_after}",
                "category-only scoring labels cannot force admission",
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

    JokerBuildValueEvaluator._direct_scoring_gain = direct_scoring_gain
    JokerAcquisitionPolicy.decide = joker_decide
    ConsumableAcquisitionPolicy.decide = consumable_decide
    VoucherAcquisitionPolicy._early_survival_gate = staticmethod(voucher_gate)

    JokerBuildValueEvaluator._rw_competence_corrections_installed = True
    JokerAcquisitionPolicy._rw_competence_corrections_installed = True
    ConsumableAcquisitionPolicy._rw_competence_corrections_installed = True
    VoucherAcquisitionPolicy._rw_competence_corrections_installed = True
