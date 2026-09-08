from __future__ import annotations

"""Phase-2 semantic cases for simple Red/White SHOP survival."""

from types import SimpleNamespace

import games.balatro.joker_policy as joker_policy_module
from games.balatro.actions import (
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    SELL_JOKER,
    BalatroAction,
)
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
    HOLD,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionOption,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
    JokerTransactionEconomics,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_policy import ShopActionScore
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollRecommendation,
    ShopRerollThresholds,
)
from games.balatro.state import BalatroState


class _ShopPolicy:
    hold_bias = 0.0

    def __init__(self, deterministic_total: float | None = None) -> None:
        self.deterministic_total = deterministic_total

    def rank_actions(self, state, actions):
        del state
        if self.deterministic_total is None:
            return []
        return [
            ShopActionScore(
                action=action,
                total=float(self.deterministic_total),
                notes=("synthetic deterministic shop option",),
            )
            for action in actions
        ]


class _RerollPolicy:
    def __init__(self, recommendation: ShopRerollRecommendation) -> None:
        self.recommendation = recommendation

    def recommend(self, state, visible_actions, *, reroll_cost, visible_score_floor=None):
        del state, visible_actions, reroll_cost, visible_score_floor
        return self.recommendation


class _JokerPolicy:
    def __init__(self, decision: JokerAcquisitionDecision | None = None) -> None:
        self.decision = decision

    def decide(self, state, candidate):
        del state, candidate
        if self.decision is None:
            raise AssertionError("unexpected Joker decision request")
        return self.decision


class _UnusedPolicy:
    def recommend(self, *args, **kwargs):
        raise AssertionError("unexpected booster recommendation request")

    def decide(self, *args, **kwargs):
        raise AssertionError("unexpected consumable decision request")


def _hold_reroll() -> ShopRerollRecommendation:
    return ShopRerollRecommendation(
        decision="HOLD",
        reroll_cost=5,
        executable_action=None,
        current_best_score=0.0,
        future_shop_ev=0.0,
        reroll_resource_cost=0.0,
        reroll_score=-1.0,
        rationale=("synthetic HOLD reroll",),
    )


def _arbiter(*, shop_policy=None, reroll=None, joker=None) -> BuildAwareShopArbiter:
    return BuildAwareShopArbiter(
        shop_policy=shop_policy or _ShopPolicy(),
        reroll_policy=_RerollPolicy(reroll or _hold_reroll()),
        joker_policy=joker or _JokerPolicy(),
        consumable_policy=_UnusedPolicy(),
        booster_policy=_UnusedPolicy(),
    )


def _base_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.ante = 2
    state.joker_slots = 5
    state.jokers = []
    state.shop_jokers = []
    state.shop_consumables = []
    return state


def _end_shop_beats_negative_admitted_child() -> SemanticCheck:
    state = _base_state()
    voucher = SimpleNamespace(name="Synthetic Voucher")
    action = BalatroAction(BUY_VOUCHER, target=voucher)
    decision = _arbiter(shop_policy=_ShopPolicy(deterministic_total=-1.0)).decide(
        state,
        [action, BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    return SemanticCheck(
        decision.action.name == END_SHOP and decision.normalized_gain == 0.0,
        observed=(
            f"action={decision.action.name}, source={decision.source}, "
            f"normalized_gain={decision.normalized_gain:.3f}"
        ),
        expected="END_SHOP beats an admitted child with negative normalized parent value",
        detail=(
            "family-local admission is not permission to spend money: D14's explicit zero-gain "
            "baseline must reject purchases that reduce run-winning shop value"
        ),
    )


def _free_reroll_wins_zero_gain_tie() -> SemanticCheck:
    state = _base_state()
    reroll = ShopRerollRecommendation(
        decision="REROLL",
        reroll_cost=0,
        executable_action=BalatroAction(REFRESH_SHOP),
        current_best_score=0.0,
        future_shop_ev=0.0,
        reroll_resource_cost=0.0,
        reroll_score=0.0,
        rationale=("synthetic free reroll tie",),
    )
    decision = _arbiter(reroll=reroll).decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=0,
    )
    return SemanticCheck(
        decision.action.name == REFRESH_SHOP and decision.source == "REROLL",
        observed=f"action={decision.action.name}, source={decision.source}",
        expected="a genuinely free reroll beats END_SHOP on an otherwise exact zero-gain tie",
        detail=(
            "a zero-cost refresh preserves money and exposes another public shop; D14's tie priority "
            "may prefer it without inventing hidden future item identities"
        ),
    )


def _replacement_stops_after_sell_checkpoint() -> SemanticCheck:
    state = _base_state()
    incumbent = SimpleNamespace(name="Incumbent", edition=None)
    candidate = SimpleNamespace(name="Candidate", edition=None, live_id="candidate")
    state.jokers = [incumbent]
    state.shop_jokers = [candidate]

    economics = JokerTransactionEconomics(
        price=5,
        sell_credit=5,
        net_spend=0,
        money_after=20,
        edition_delta=0.0,
        price_penalty=0.0,
        interest_penalty=0.0,
        reserve_penalty=0.0,
        slot_penalty=0.0,
    )
    option = JokerAcquisitionOption(
        mode=REPLACE,
        build_gain=5.0,
        total_advantage=5.0,
        economics=economics,
        eligible=True,
        replace_index=0,
    )
    joker_decision = JokerAcquisitionDecision(
        action=REPLACE,
        candidate="Candidate",
        selected=option,
        options=(option,),
        thresholds=JokerAcquisitionThresholds(),
        rationale=("synthetic profitable replacement",),
    )

    decision = _arbiter(joker=_JokerPolicy(joker_decision)).decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    fresh_checkpoint = any(
        "fresh authoritative observation" in note for note in decision.rationale
    )
    return SemanticCheck(
        decision.action.name == SELL_JOKER
        and decision.action.target == 0
        and decision.source == "JOKER_REPLACE_SELL"
        and fresh_checkpoint,
        observed=(
            f"action={decision.action.name}, target={decision.action.target}, "
            f"source={decision.source}, fresh_checkpoint={fresh_checkpoint}"
        ),
        expected="replacement executes only SELL_JOKER, then requires fresh observation before BUY",
        detail=(
            "shop replacement is a two-checkpoint transaction; D14 must not chain a projected purchase "
            "against stale money, slots, or visible-shop state"
        ),
    )


def _paid_reroll_respects_absolute_cost_cap() -> SemanticCheck:
    state = _base_state()
    state.money = 50
    thresholds = ShopRerollThresholds(
        maximum_paid_reroll_cost=8,
        minimum_money_after_paid_reroll=0,
    )
    policy = BuildAwareShopRerollPolicy(thresholds=thresholds)
    recommendation = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=9,
        visible_score_floor=0.0,
    )
    capped = any("stop-loss cap" in note for note in recommendation.rationale)
    return SemanticCheck(
        recommendation.decision == "HOLD"
        and recommendation.executable_action is None
        and capped,
        observed=(
            f"decision={recommendation.decision}, executable={recommendation.executable_action}, "
            f"cap_reason={capped}"
        ),
        expected="paid reroll above the configured absolute cost cap fails closed",
        detail=(
            "future-shop option value cannot justify an arbitrarily expensive refresh; D11 must enforce "
            "its explicit paid-reroll stop-loss before estimating hidden-offer EV"
        ),
    )


def _paid_reroll_preserves_minimum_cash_reserve() -> SemanticCheck:
    state = _base_state()
    state.money = 12
    thresholds = ShopRerollThresholds(
        maximum_paid_reroll_cost=8,
        minimum_money_after_paid_reroll=10,
    )
    policy = BuildAwareShopRerollPolicy(thresholds=thresholds)
    recommendation = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=3,
        visible_score_floor=0.0,
    )
    reserve_block = any("stop-loss reserve" in note for note in recommendation.rationale)
    return SemanticCheck(
        recommendation.decision == "HOLD"
        and recommendation.executable_action is None
        and reserve_block,
        observed=(
            f"decision={recommendation.decision}, money={state.money}, reroll_cost=3, "
            f"reserve_reason={reserve_block}"
        ),
        expected="paid reroll is rejected when it would cross the minimum cash-after-reroll reserve",
        detail=(
            "simple Red/White survival requires cash to remain available for visible scoring purchases; "
            "D11 must reject a paid refresh before future-shop EV when the post-reroll reserve is unsafe"
        ),
    )


def _synthetic_transition(build_gain: float) -> JokerBuildTransitionPlanner:
    planner = JokerBuildTransitionPlanner()
    planner.evaluator = SimpleNamespace(
        evaluate=lambda state, candidate: SimpleNamespace(total_gain=float(build_gain))
    )
    planner.plan = lambda state, candidate: SimpleNamespace(
        candidate_value=SimpleNamespace(
            applicability="APPLICABLE",
            total_gain=float(build_gain),
        ),
        alternatives=(),
    )
    return planner


def _decide_without_bond(
    policy: JokerAcquisitionPolicy,
    state: BalatroState,
    candidate: FlatMultJoker,
) -> JokerAcquisitionDecision:
    original = joker_policy_module._bond_transition_bonus
    joker_policy_module._bond_transition_bonus = lambda state, candidate, **kwargs: (0.0, ())
    try:
        return policy.decide(state, candidate)
    finally:
        joker_policy_module._bond_transition_bonus = original


def _first_engine_bootstrap_does_not_rescue_zero_cash() -> SemanticCheck:
    state = _base_state()
    state.ante = 1
    state.money = 6
    candidate = FlatMultJoker(4)
    candidate.cost = 6
    policy = JokerAcquisitionPolicy(
        transition_planner=_synthetic_transition(0.50),
    )
    decision = _decide_without_bond(policy, state, candidate)
    option = decision.options[0]
    return SemanticCheck(
        decision.action == HOLD
        and option.economics.money_after == 0
        and abs(float(option.build_gain) - 0.50) <= 1e-9,
        observed=(
            f"action={decision.action}, build_gain={option.build_gain:.3f}, "
            f"money_after={option.economics.money_after}"
        ),
        expected="the early first-engine bootstrap does not rescue a marginal buy that leaves zero cash",
        detail=(
            "Ante-1/2 first-engine relaxation is deliberately bounded: positive scoring value may relax "
            "reserve preference only when at least one dollar remains after the purchase"
        ),
    )


def _ordinary_joker_buy_prices_reserve_crossing() -> SemanticCheck:
    state = _base_state()
    state.ante = 3
    state.money = 6
    state.jokers = [FlatMultJoker(4)]
    candidate = FlatMultJoker(4)
    candidate.cost = 4
    thresholds = JokerAcquisitionThresholds(
        minimum_purchase_advantage=0.35,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_target=5,
        reserve_weight=1.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )
    policy = JokerAcquisitionPolicy(
        thresholds=thresholds,
        transition_planner=_synthetic_transition(1.50),
    )
    decision = _decide_without_bond(policy, state, candidate)
    option = decision.options[0]
    return SemanticCheck(
        decision.action == HOLD
        and abs(option.economics.reserve_penalty - 3.0) <= 1e-9
        and abs(float(option.build_gain) - 1.50) <= 1e-9
        and option.total_advantage < thresholds.minimum_purchase_advantage,
        observed=(
            f"action={decision.action}, build_gain={option.build_gain:.3f}, "
            f"reserve_penalty={option.economics.reserve_penalty:.3f}, "
            f"advantage={option.total_advantage:.3f}"
        ),
        expected="ordinary D2 purchase value prices the incremental cash-reserve shortfall",
        detail=(
            "once the first-engine exception no longer applies, a marginal Joker must not be treated as "
            "free of survival cost when its purchase crosses the configured cash reserve"
        ),
    )


RED_WHITE_PHASE2_SHOP_CASES = (
    SemanticBenchmarkCase(
        case_id="shop.simple.end_shop_zero_baseline",
        category="SHOP_SURVIVAL",
        description="END_SHOP rejects negative normalized child value",
        evaluate=_end_shop_beats_negative_admitted_child,
        source="Phase 2 simple-shop audit: no-action survival baseline",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.free_reroll_zero_tie",
        category="SHOP_SURVIVAL",
        description="free reroll wins an exact zero-gain END_SHOP tie",
        evaluate=_free_reroll_wins_zero_gain_tie,
        source="Phase 2 simple-shop audit: free information option",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.replacement_reobserve_boundary",
        category="SHOP_SURVIVAL",
        description="Joker replacement stops after the sell checkpoint",
        evaluate=_replacement_stops_after_sell_checkpoint,
        source="Phase 2 simple-shop audit: transactional re-observation",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.paid_reroll_cost_cap",
        category="SHOP_SURVIVAL",
        description="paid reroll respects the absolute stop-loss cost cap",
        evaluate=_paid_reroll_respects_absolute_cost_cap,
        source="Phase 2 simple-shop audit: paid reroll stop-loss",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.paid_reroll_cash_reserve",
        category="SHOP_SURVIVAL",
        description="paid reroll preserves minimum post-refresh cash reserve",
        evaluate=_paid_reroll_preserves_minimum_cash_reserve,
        source="Phase 2 simple-shop audit: cash reserve boundary",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.first_engine_zero_cash_guard",
        category="SHOP_SURVIVAL",
        description="first-engine bootstrap does not rescue a zero-cash marginal buy",
        evaluate=_first_engine_bootstrap_does_not_rescue_zero_cash,
        source="Phase 2 simple-shop audit: bounded first-engine reserve relaxation",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.joker_reserve_crossing_cost",
        category="SHOP_SURVIVAL",
        description="ordinary Joker purchases price reserve-crossing survival cost",
        evaluate=_ordinary_joker_buy_prices_reserve_crossing,
        source="Phase 2 simple-shop audit: ordinary purchase reserve economics",
    ),
)
