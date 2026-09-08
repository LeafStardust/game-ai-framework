from __future__ import annotations

from types import SimpleNamespace

from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.early_spend_sanity_policy import (
    _allow_empty_roster_buffoon_floor_exception,
)
from games.balatro.joker_policy import (
    HOLD,
    JokerAcquisitionOption,
    JokerAcquisitionPolicy,
    JokerTransactionEconomics,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_booster_policy import BUY as BOOSTER_BUY
from games.balatro.shop_booster_policy import HOLD as BOOSTER_HOLD
from games.balatro.shop_consumable_policy import BUY_AND_USE, ConsumableAcquisitionPolicy
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy
from games.balatro.state import BalatroState


class _WheelConsumable(Consumable):
    name = "The Wheel of Fortune"
    category = "TAROT"
    price = 4

    def can_use(self, context: ConsumableContext) -> bool:
        return bool(tuple(getattr(context.state, "jokers", ()) or ()))

    def use(self, context: ConsumableContext) -> ConsumableContext:
        return context


def _d2_first_engine_keeps_conflict_veto() -> SemanticCheck:
    policy = JokerAcquisitionPolicy(
        transition_planner=SimpleNamespace(
            plan=lambda state, candidate: SimpleNamespace(
                candidate_value=SimpleNamespace(
                    applicability="CONFLICT",
                    total_gain=10.0,
                ),
                alternatives=(),
            )
        )
    )
    economics = JokerTransactionEconomics(
        price=4,
        sell_credit=0,
        net_spend=4,
        money_after=3,
        edition_delta=0.0,
        price_penalty=0.0,
        interest_penalty=0.0,
        reserve_penalty=0.0,
        slot_penalty=0.0,
    )
    policy._score_add = lambda state, candidate, build_gain, strategic_conflict=False: JokerAcquisitionOption(
        mode="BUY",
        build_gain=float(build_gain),
        total_advantage=-1.0,
        economics=economics,
        eligible=not strategic_conflict,
        rationale=(),
    )
    state = SimpleNamespace(
        ante=1,
        money=7,
        jokers=[],
        joker_slots=5,
    )
    decision = policy.decide(state, FlatMultJoker(4))
    return SemanticCheck(
        decision.action == HOLD,
        observed=f"action={decision.action}",
        expected="HOLD",
        detail=(
            "the native Ante-1/2 first-engine reserve relaxation may admit positive "
            "grounded value, but it must not override D2 strategic-conflict ineligibility"
        ),
    )


def _d3_hand_size_waits_for_first_engine() -> SemanticCheck:
    empty_state = SimpleNamespace(jokers=(), hand_levels={"PAIR": 1})
    empty_profile = SimpleNamespace(
        ante=1,
        joker_names=(),
        hand_levels=(("PAIR", 1),),
    )
    blocked, blocked_notes = VoucherAcquisitionPolicy._early_survival_gate(
        empty_state,
        empty_profile,
        "Paint Brush",
        price=10,
        money_after=5,
    )

    established_state = SimpleNamespace(jokers=(object(),), hand_levels={"PAIR": 1})
    established_profile = SimpleNamespace(
        ante=1,
        joker_names=("FlatMultJoker",),
        hand_levels=(("PAIR", 1),),
    )
    admitted, admitted_notes = VoucherAcquisitionPolicy._early_survival_gate(
        established_state,
        established_profile,
        "Paint Brush",
        price=10,
        money_after=5,
    )

    passed = not blocked and admitted
    return SemanticCheck(
        passed,
        observed=(
            f"empty_allowed={blocked}, established_allowed={admitted}, "
            f"empty_notes={blocked_notes!r}, established_notes={admitted_notes!r}"
        ),
        expected="empty board HOLD; established board keeps Paint Brush structural exception",
        detail=(
            "D3 itself owns the first-engine readiness boundary; no late Red/White "
            "voucher wrapper is required"
        ),
    )


def _d4_wheel_exposes_buy_and_use() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.consumables = []
    state.consumable_slots = 2
    state.jokers = [FlatMultJoker(4)]
    state.joker_slots = 5

    decision = ConsumableAcquisitionPolicy().decide(state, _WheelConsumable())
    selected = decision.selected
    passed = (
        decision.action == BUY_AND_USE
        and selected is not None
        and selected.executable_action is not None
        and float(selected.build_gain) > 0.0
    )
    return SemanticCheck(
        passed,
        observed=(
            f"action={decision.action}, build_gain="
            f"{None if selected is None else selected.build_gain}"
        ),
        expected="BUY_AND_USE candidate with positive analytic edition expectation",
        detail=(
            "D4 must expose Wheel to D14 when public edition expectation is positive; "
            "D14, not a late correction wrapper, decides whether the purchase wins globally"
        ),
    )


def _d8_empty_roster_buffoon_keeps_positive_admission() -> SemanticCheck:
    empty = SimpleNamespace(joker_names=())
    established = SimpleNamespace(joker_names=("FlatMultJoker",))
    buffoon_buy = SimpleNamespace(decision=BOOSTER_BUY, family="BUFFOON")
    buffoon_hold = SimpleNamespace(decision=BOOSTER_HOLD, family="BUFFOON")
    celestial_buy = SimpleNamespace(decision=BOOSTER_BUY, family="CELESTIAL")

    empty_buy = _allow_empty_roster_buffoon_floor_exception(empty, buffoon_buy)
    established_buy = _allow_empty_roster_buffoon_floor_exception(established, buffoon_buy)
    empty_hold = _allow_empty_roster_buffoon_floor_exception(empty, buffoon_hold)
    wrong_family = _allow_empty_roster_buffoon_floor_exception(empty, celestial_buy)
    passed = empty_buy and not established_buy and not empty_hold and not wrong_family
    return SemanticCheck(
        passed,
        observed=(
            f"empty_buy={empty_buy}, established_buy={established_buy}, "
            f"empty_hold={empty_hold}, celestial_buy={wrong_family}"
        ),
        expected="exception only for an already-admitted Buffoon BUY on an empty Joker roster",
        detail=(
            "the early cash-floor guard may stop suppressing positive first-engine Buffoon EV, "
            "but it must not create admission for HOLDs, other booster families, or established builds"
        ),
    )


RED_WHITE_NATIVE_SHOP_CASES = (
    SemanticBenchmarkCase(
        case_id="d2.authority.first_engine_conflict",
        category="SHOP_SURVIVAL",
        description="native D2 first-engine bootstrap preserves strategic-conflict veto",
        evaluate=_d2_first_engine_keeps_conflict_veto,
    ),
    SemanticBenchmarkCase(
        case_id="d3.authority.first_engine_capacity",
        category="SHOP_SURVIVAL",
        description="native D3 hand-size readiness waits for the first scoring foothold",
        evaluate=_d3_hand_size_waits_for_first_engine,
    ),
    SemanticBenchmarkCase(
        case_id="d4.authority.wheel_shop_admission",
        category="SHOP_SURVIVAL",
        description="native D4 exposes positive Wheel edition expectation to D14",
        evaluate=_d4_wheel_exposes_buy_and_use,
    ),
    SemanticBenchmarkCase(
        case_id="d8.authority.empty_roster_buffoon",
        category="SHOP_SURVIVAL",
        description="D8 preserves positive empty-roster Buffoon admission through the early cash floor",
        evaluate=_d8_empty_roster_buffoon_keeps_positive_admission,
        source="Live three-run gate: Ante-1 zero-engine shop passivity",
    ),
)
