from __future__ import annotations

"""Final Red/White competence corrections derived from live-run failures.

This layer is intentionally small and semantic. It does not predict hidden shop
contents or draw order. It corrects recurring public-state mistakes observed in
live Red/White runs:

* an empty early scoring engine could reject an affordable direct-scoring Joker;
* early utility purchases could outrank incomplete scoring coverage;
* Bond/coherence value could outrank a missing chips or Mult/XMult axis;
* a full flat roster could refuse a positive scaling replacement;
* pace recovery could waste equal-cost discard tokens on repeated singletons;
* shop Wheel of Fortune was never admitted by the deterministic D4 immediate-use
  path, even with healthy money and eligible editionless Jokers.

The module installs after the existing policy stack so mechanical/conflict vetoes
remain authoritative and these corrections see the final public decision.
"""

from dataclasses import replace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
from games.balatro.build.effects import SCORE_CHIPS, SCORE_MULT, SCORE_XMULT
from games.balatro.build.joker_lifecycle import STATEFUL_SCALING
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.joker_policy import BUY, HOLD, REPLACE, JokerAcquisitionPolicy
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.shop_consumable_policy import (
    BUY_AND_USE,
    HOLD as CONSUMABLE_HOLD,
    ConsumableAcquisitionOption,
    ConsumableAcquisitionPolicy,
)
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy


EARLY_ENGINE_ANTE_LIMIT = 2
SCORING_COVERAGE_ANTE_LIMIT = 4
FIRST_ENGINE_MINIMUM_CASH_AFTER = 1
FIRST_ENGINE_VOUCHER_RESERVE = 10
EARLY_SCORING_VOUCHER_PRICE = 8
EXPENSIVE_HAND_SIZE_VOUCHERS = frozenset({"Paint Brush", "Palette"})
REDRAW_EFFICIENCY_BASE = 16.0
REDRAW_EFFICIENCY_SHORTFALL_WEIGHT = 16.0
EMPTY_SCORING_ROSTER_BONUS = 8.0
MISSING_MULT_AXIS_BONUS = 7.0
MISSING_CHIP_AXIS_BONUS = 4.0
MISSING_SCALER_REPLACEMENT_BONUS = 4.0
WHEEL_NAMES = frozenset({"The Wheel of Fortune", "Wheel of Fortune"})
WHEEL_SHOP_OPTION_FLOOR = 1.25


_ANALYZER = ScenarioJokerBehaviorAnalyzer()


def _ante(state) -> int:
    for name in ("ante", "ante_num"):
        try:
            value = int(getattr(state, name, 0) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def _descriptor(candidate: object):
    try:
        return _ANALYZER.describe(candidate)
    except (AttributeError, TypeError, ValueError):
        return None


def _scoring_axes(candidate: object) -> frozenset[str]:
    descriptor = _descriptor(candidate)
    if descriptor is None:
        return frozenset()
    outputs = set(descriptor.produces) | set(descriptor.transforms)
    return frozenset(outputs.intersection({SCORE_CHIPS, SCORE_MULT, SCORE_XMULT}))


def _is_stateful_scaler(candidate: object) -> bool:
    descriptor = _descriptor(candidate)
    return bool(descriptor is not None and STATEFUL_SCALING in descriptor.produces)


def _roster_scoring_axes(state) -> frozenset[str]:
    axes: set[str] = set()
    for joker in tuple(getattr(state, "jokers", ()) or ()):
        axes.update(_scoring_axes(joker))
    return frozenset(axes)


def _roster_has_stateful_scaler(state) -> bool:
    return any(
        _is_stateful_scaler(joker)
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _direct_scoring_candidate(candidate: object) -> bool:
    return bool(_scoring_axes(candidate))


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


def _coverage_note(existing: frozenset[str], candidate: frozenset[str]) -> tuple[float, tuple[str, ...]]:
    if not candidate:
        return 0.0, ()

    bonus = 0.0
    notes: list[str] = []
    if not existing:
        bonus += EMPTY_SCORING_ROSTER_BONUS
        notes.append("survival scoring coverage: roster has no direct scoring axis")
        return bonus, tuple(notes)

    has_mult_axis = bool(existing.intersection({SCORE_MULT, SCORE_XMULT}))
    candidate_mult_axis = bool(candidate.intersection({SCORE_MULT, SCORE_XMULT}))
    if not has_mult_axis and candidate_mult_axis:
        bonus += MISSING_MULT_AXIS_BONUS
        notes.append("survival scoring coverage: candidate supplies missing Mult/XMult axis")

    if SCORE_CHIPS not in existing and SCORE_CHIPS in candidate:
        bonus += MISSING_CHIP_AXIS_BONUS
        notes.append("survival scoring coverage: candidate supplies missing chips axis")

    return bonus, tuple(notes)


def install_red_white_competence_corrections() -> None:
    if getattr(JokerAcquisitionPolicy, "_rw_competence_corrections_installed", False):
        return

    original_joker_decide = JokerAcquisitionPolicy.decide
    original_consumable_decide = ConsumableAcquisitionPolicy.decide
    original_voucher_gate = VoucherAcquisitionPolicy._early_survival_gate
    original_discard_value = LiveHandDecisionEvaluator._discard_value
    original_joker_gain = ShopUtilityScale.joker_gain

    def joker_decide(self, state, candidate):
        decision = original_joker_decide(self, state, candidate)
        ante = _ante(state)

        if decision.action == HOLD:
            # Recover the first scoring foothold even when a scaler's current build
            # gain is still zero before it has had a chance to scale.
            if (
                1 <= ante <= EARLY_ENGINE_ANTE_LIMIT
                and not tuple(getattr(state, "jokers", ()) or ())
                and _direct_scoring_candidate(candidate)
            ):
                affordable = [
                    option
                    for option in tuple(getattr(decision, "options", ()) or ())
                    if getattr(option, "mode", None) == BUY
                    and int(getattr(getattr(option, "economics", None), "money_after", -1))
                    >= FIRST_ENGINE_MINIMUM_CASH_AFTER
                ]
                if affordable:
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

            # A full flat roster with no scaler repeatedly rerolled past positive
            # scaling candidates in live play. Rescue only already-positive,
            # reserve-safe replacement options; negative or unaffordable churn stays
            # rejected, as do all mechanical sale restrictions encoded by D2.
            jokers = tuple(getattr(state, "jokers", ()) or ())
            if (
                ante >= 3
                and len(jokers) >= int(getattr(state, "joker_slots", len(jokers)) or len(jokers))
                and not _roster_has_stateful_scaler(state)
                and _is_stateful_scaler(candidate)
                and _direct_scoring_candidate(candidate)
            ):
                replacements = [
                    option
                    for option in tuple(getattr(decision, "options", ()) or ())
                    if getattr(option, "mode", None) == REPLACE
                    and float(getattr(option, "total_advantage", float("-inf"))) > 0.0
                    and int(getattr(getattr(option, "economics", None), "money_after", -1))
                    >= int(getattr(self.thresholds, "reserve_target", 0))
                    and getattr(option, "replace_index", None) is not None
                ]
                if replacements:
                    raw_selected = max(
                        replacements,
                        key=lambda option: (
                            float(getattr(option, "total_advantage", float("-inf"))),
                            float(getattr(option, "build_gain", 0.0) or 0.0),
                        ),
                    )
                    selected = replace(raw_selected, eligible=True)
                    options = tuple(
                        selected if option is raw_selected else option
                        for option in tuple(getattr(decision, "options", ()) or ())
                    )
                    return replace(
                        decision,
                        action=REPLACE,
                        selected=selected,
                        options=options,
                        rationale=(
                            *tuple(getattr(decision, "rationale", ()) or ()),
                            "flat-roster repair: positive reserve-safe scoring scaler replacement admitted",
                        ),
                    )

        return decision

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

        ante = _ante(state)
        if ante <= 0:
            try:
                ante = int(getattr(profile, "ante", 0) or 0)
            except (TypeError, ValueError):
                ante = 0
        if ante < 1 or ante > EARLY_ENGINE_ANTE_LIMIT:
            return True, notes

        state_roster = tuple(getattr(state, "jokers", ()) or ())
        state_jokers = len(state_roster)
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

        # Live attempt 2 bought Reroll Surplus with one conditional Mult Joker while
        # visible scoring upgrades were still needed. Use real Joker semantics when
        # available; profiler-only unit tests retain D3's canonical structural
        # exceptions because string names cannot establish score axes safely.
        if (
            state_roster
            and not invested_hand
            and int(price) >= EARLY_SCORING_VOUCHER_PRICE
        ):
            axes = _roster_scoring_axes(state)
            has_chips = SCORE_CHIPS in axes
            has_mult = bool(axes.intersection({SCORE_MULT, SCORE_XMULT}))
            if not (has_chips and has_mult):
                return False, (
                    *tuple(notes or ()),
                    "D3 scoring-coverage hold: expensive utility waits until both chips and Mult/XMult axes exist",
                    f"D3 scoring axes={sorted(axes)} price=${int(price)} money_after=${int(money_after)}",
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

        # A discard token costs the same whether one or five cards are redrawn.
        # The previous weight still lost to retained-structure promise and produced
        # four consecutive singletons in live runs, so make fixed-token efficiency
        # material while remaining proportional to the actual pace shortfall.
        extra_redraws = min(4, redraws - 1)
        efficiency = extra_redraws * (
            REDRAW_EFFICIENCY_BASE
            + REDRAW_EFFICIENCY_SHORTFALL_WEIGHT * shortfall
        )
        return value + efficiency

    def joker_gain(self, state, executable):
        utility = original_joker_gain(self, state, executable)
        candidate = getattr(executable, "candidate", None)
        if candidate is None or utility.gain <= 0.0:
            return utility
        if joker_has_negative_edition(candidate):
            # Negative edition value is already canonical and slot-neutral in D14.
            # Do not layer Red/White coverage utility onto that exact contract.
            return utility
        ante = _ante(state)
        if ante < 1 or ante > SCORING_COVERAGE_ANTE_LIMIT:
            return utility

        existing = _roster_scoring_axes(state)
        candidate_axes = _scoring_axes(candidate)
        bonus, notes = _coverage_note(existing, candidate_axes)

        replacement = getattr(executable, "source", "") == "JOKER_REPLACE_SELL"
        if (
            replacement
            and not _roster_has_stateful_scaler(state)
            and _is_stateful_scaler(candidate)
            and candidate_axes
        ):
            bonus += MISSING_SCALER_REPLACEMENT_BONUS
            notes = (
                *notes,
                "flat-roster repair: first scoring scaler gets replacement priority",
            )

        if bonus <= 0.0:
            return utility
        return ShopNormalizedUtility(
            gain=float(utility.gain) + bonus,
            resource_cost=utility.resource_cost,
            notes=(
                *utility.notes,
                *notes,
                f"Red/White survival scoring bonus={bonus:.3f}",
                "coverage bonus is public-state only and does not predict future shops",
            ),
        )

    JokerAcquisitionPolicy.decide = joker_decide
    ConsumableAcquisitionPolicy.decide = consumable_decide
    VoucherAcquisitionPolicy._early_survival_gate = staticmethod(voucher_gate)
    LiveHandDecisionEvaluator._discard_value = discard_value
    ShopUtilityScale.joker_gain = joker_gain

    JokerAcquisitionPolicy._rw_competence_corrections_installed = True
    ConsumableAcquisitionPolicy._rw_competence_corrections_installed = True
    VoucherAcquisitionPolicy._rw_competence_corrections_installed = True
    LiveHandDecisionEvaluator._rw_competence_corrections_installed = True
    ShopUtilityScale._rw_competence_corrections_installed = True