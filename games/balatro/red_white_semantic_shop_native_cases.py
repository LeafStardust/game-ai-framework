from __future__ import annotations

from types import SimpleNamespace

from games.balatro.joker_policy import (
    HOLD,
    JokerAcquisitionOption,
    JokerAcquisitionPolicy,
    JokerTransactionEconomics,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy


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
)
