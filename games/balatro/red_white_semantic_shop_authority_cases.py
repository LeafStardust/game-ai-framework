from __future__ import annotations

"""Semantic authority checks for canonical D14 visible-shop planning."""

from dataclasses import replace

from games.balatro.actions import BUY_JOKER
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    JokerAcquisitionDecision,
    JokerAcquisitionOption,
    JokerAcquisitionThresholds,
    JokerTransactionEconomics,
)
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_utility_scale import ShopNormalizedUtility


class _State:
    def __init__(self, *, shop_jokers, jokers=()):
        self.phase = "SHOP"
        self.money = 20
        self.joker_slots = 5
        self.shop_jokers = list(shop_jokers)
        self.jokers = list(jokers)

    def copy(self):
        clone = _State(shop_jokers=self.shop_jokers, jokers=self.jokers)
        clone.phase = self.phase
        clone.money = self.money
        clone.joker_slots = self.joker_slots
        return clone


class _Candidate:
    def __init__(self, label: str):
        self.label = label
        self.name = label
        self.live_id = label
        self.area_index = None
        self.edition = None


class _UtilityScale:
    def joker_gain(self, state, executable):
        gain = -0.10 if not tuple(state.jokers) else 2.00
        return ShopNormalizedUtility(
            gain=gain,
            notes=(f"synthetic normalized Joker gain={gain:.2f}",),
        )


def _economics() -> JokerTransactionEconomics:
    return JokerTransactionEconomics(
        price=0,
        sell_credit=0,
        net_spend=0,
        money_after=20,
        edition_delta=0.0,
        price_penalty=0.0,
        interest_penalty=0.0,
        reserve_penalty=0.0,
        slot_penalty=0.0,
    )


def _hold_decision(candidate, *, build_gain: float = 1.0) -> JokerAcquisitionDecision:
    option = JokerAcquisitionOption(
        mode=BUY,
        build_gain=build_gain,
        total_advantage=-0.10,
        economics=_economics(),
        eligible=True,
    )
    return JokerAcquisitionDecision(
        action=HOLD,
        candidate=candidate.label,
        selected=None,
        options=(option,),
        thresholds=JokerAcquisitionThresholds(),
        rationale=("standalone threshold holds candidate",),
    )


def _buy_after_projection(
    decision: JokerAcquisitionDecision,
    *,
    build_gain: float,
) -> JokerAcquisitionDecision:
    option = replace(
        decision.options[0],
        build_gain=build_gain,
        total_advantage=1.50,
    )
    return replace(
        decision,
        action=BUY,
        selected=option,
        options=(option,),
        rationale=("projected companion makes candidate a real D2 BUY",),
    )


class _PairPolicy:
    def __init__(self, *, projected_build_gain: float):
        self.projected_build_gain = projected_build_gain

    def decide(self, state, candidate):
        base = _hold_decision(candidate)
        if tuple(state.jokers):
            return _buy_after_projection(
                base,
                build_gain=self.projected_build_gain,
            )
        return base


def _arbiter_for(policy) -> BuildAwareShopArbiter:
    arbiter = BuildAwareShopArbiter(joker_policy=policy)
    arbiter.utility_scale = _UtilityScale()
    return arbiter


def _native_pair_is_d14_candidate() -> SemanticCheck:
    first = _Candidate("First")
    second = _Candidate("Second")
    state = _State(shop_jokers=(first, second))
    arbiter = _arbiter_for(_PairPolicy(projected_build_gain=3.0))

    pair = arbiter._best_visible_bond_pair(state)
    passed = (
        pair is not None
        and pair.first.action.name == BUY_JOKER
        and abs(pair.combined_gain - 1.90) <= 1e-9
        and pair.interaction_gain > 0.0
    )
    return SemanticCheck(
        passed,
        observed=(
            "none"
            if pair is None
            else f"action={pair.first.action.name}, combined={pair.combined_gain:.3f}, interaction={pair.interaction_gain:.3f}"
        ),
        expected="verified visible two-Joker plan is produced by canonical BuildAwareShopArbiter",
        detail="the pair is a normalized D14 candidate rather than a post-arbiter strategy rescue",
    )


def _pair_requires_real_interaction_gain() -> SemanticCheck:
    first = _Candidate("First")
    second = _Candidate("Second")
    state = _State(shop_jokers=(first, second))
    arbiter = _arbiter_for(_PairPolicy(projected_build_gain=1.0))

    pair = arbiter._best_visible_bond_pair(state)
    return SemanticCheck(
        pair is None,
        observed="none" if pair is None else f"combined={pair.combined_gain:.3f}",
        expected="no pair candidate when the first purchase does not improve the second Joker's D2 build value",
        detail="two unrelated speculative HOLD Jokers must not bypass ordinary D2 admission through the D14 pair planner",
    )


RED_WHITE_SHOP_AUTHORITY_CASES = (
    SemanticBenchmarkCase(
        case_id="d14.authority.visible_bond_pair",
        category="SHOP_SURVIVAL",
        description="visible two-Joker planning is native D14 candidate evidence",
        evaluate=_native_pair_is_d14_candidate,
    ),
    SemanticBenchmarkCase(
        case_id="d14.authority.pair_requires_interaction",
        category="SHOP_SURVIVAL",
        description="D14 pair planning requires mechanical/composition interaction gain",
        evaluate=_pair_requires_real_interaction_gain,
    ),
)
