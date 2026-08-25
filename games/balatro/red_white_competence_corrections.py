from __future__ import annotations

"""Final Red/White competence corrections derived from live-run failures.

This layer is intentionally small and semantic. It does not predict hidden shop
contents or draw order. It corrects four public-state mistakes observed in live
Red/White runs:

* an empty early scoring engine could reject an affordable direct-scoring Joker
  because reserve economics outweighed the first foothold;
* Paint Brush/Palette could bypass early survival readiness with zero Jokers;
* pace recovery treated a one-card discard too similarly to a multi-card redraw
  even though both consume exactly one discard resource;
* shop Wheel of Fortune was never admitted by the deterministic D4 immediate-use
  path, even with healthy money and eligible editionless Jokers.

The module installs after the existing policy stack so all mechanical/conflict
vetoes remain authoritative and these corrections see the final public decision.
"""

from dataclasses import replace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.joker_policy import BUY, HOLD, JokerAcquisitionPolicy
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
# The pack path already gives Wheel a public-state stochastic expectation. Shop
# Wheel additionally has collection/edition option value requested by the Red/White
# competence policy; D14 still subtracts the shared real money cost before buying.
WHEEL_SHOP_OPTION_FLOOR = 1.25


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
        descriptor = ScenarioJokerBehaviorAnalyzer().describe(candidate)
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

        # The whole point of this correction is to recover first-engine scalers whose
        # *current* build gain is zero before they have had a chance to scale (Square
        # Joker is the live-run example). Core D2 therefore marks the otherwise valid
        # BUY option ineligible. Requiring option.eligible here would simply reproduce
        # that failure. In this deliberately narrow zero-roster/early-ante state,
        # semantic direct scoring plus affordability is sufficient admission; D14
        # still compares the resulting purchase on the shared money/interest scale.
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
        expected_gain = max(
            WHEEL_SHOP_OPTION_FLOOR,
            float(expectation.expected_build_gain),
        )
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
                f"analytic expected edition gain={float(expectation.expected_build_gain):.3f}",
                f"Red/White Wheel option floor={WHEEL_SHOP_OPTION_FLOOR:.3f}",
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

        # D3's profiler is the canonical readiness snapshot. Some focused policy
        # tests intentionally pass a skeletal state object while supplying the real
        # Joker/hand readiness through the profile, so consult both instead of
        # treating an absent state field as an empty live roster.
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

        # This correction targets the observed $14->$4 empty-engine Paint Brush
        # failure. A healthy bankroll should retain the canonical structural voucher
        # exception, and any established scoring foothold should do the same.
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

        # Debuffed-card preference is already owned by d1_debuff_recovery_policy.
        # Do not duplicate that weight here: this layer only corrects the fixed-cost
        # redraw inefficiency that caused repeated one-card discards.
        if redraws <= 1:
            return value
        if int(getattr(state, "discards_remaining", 0) or 0) <= 1:
            return value

        # One discard token is spent whether one card or five are redrawn. Reward
        # additional redraws only while the current hand is below required pace;
        # retained-structure and card-effect costs from the canonical evaluator still
        # decide whether those extra cards are actually safe to throw away.
        extra_redraws = min(4, redraws - 1)
        efficiency = extra_redraws * (
            REDRAW_EFFICIENCY_BASE
            + REDRAW_EFFICIENCY_SHORTFALL_WEIGHT * shortfall
        )
        return value + efficiency

    JokerAcquisitionPolicy.decide = joker_decide
    ConsumableAcquisitionPolicy.decide = consumable_decide
    VoucherAcquisitionPolicy._early_survival_gate = staticmethod(voucher_gate)
    LiveHandDecisionEvaluator._discard_value = discard_value

    JokerAcquisitionPolicy._rw_competence_corrections_installed = True
    ConsumableAcquisitionPolicy._rw_competence_corrections_installed = True
    VoucherAcquisitionPolicy._rw_competence_corrections_installed = True
    LiveHandDecisionEvaluator._rw_competence_corrections_installed = True
