from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import BUY_VOUCHER, BalatroAction
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_voucher_policy import (
    HOLD,
    VoucherAcquisitionPolicy,
    VoucherAcquisitionThresholds,
)
from games.balatro.state import BalatroState
from games.balatro.voucher_parent_literal_policy import VoucherParentLiteralEvaluator


class _Voucher:
    def __init__(self, label: str, *, price: int) -> None:
        self.label = label
        self.name = label
        self.price = int(price)


class _HighVoucherEstimator:
    def estimate(self, state, action):
        return 100.0, ("synthetic high persistent value",)


class _NeutralProfiler:
    def profile(self, state):
        return SimpleNamespace(
            ante=int(state.ante),
            money=int(state.money),
            free_joker_slots=max(0, int(state.joker_slots) - len(state.jokers)),
            joker_names=tuple(
                str(getattr(joker, "name", getattr(joker, "label", type(joker).__name__)))
                for joker in state.jokers
            ),
            hand_levels=dict(state.hand_levels),
        )


def _hard_post_purchase_reserve_blocks_voucher() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 4
    state.money = 8
    candidate = _Voucher("Grabber", price=5)
    thresholds = VoucherAcquisitionThresholds(
        minimum_money_after=5,
        minimum_persistent_value=0.0,
        minimum_purchase_advantage=0.0,
    )
    policy = VoucherAcquisitionPolicy(
        thresholds,
        item_value_estimator=_HighVoucherEstimator(),
        profiler=_NeutralProfiler(),
    )

    decision = policy.decide(state, candidate)
    passed = (
        decision.action == HOLD
        and decision.executable_action is None
        and decision.money_after == 3
        and decision.persistent_value > 0.0
    )
    return SemanticCheck(
        passed,
        observed=(
            f"decision={decision.action}, money_after={decision.money_after}, "
            f"minimum={decision.thresholds.minimum_money_after}, persistent={decision.persistent_value:.3f}"
        ),
        expected="D3 HOLDs even a high-value persistent voucher when the purchase breaches its hard post-purchase cash floor",
        detail=(
            "permanent value cannot override current-run liquidity: D3 minimum_money_after is an admission gate, "
            "not a soft utility term that horizon or build value may buy through"
        ),
    )


def _early_expensive_voucher_cannot_preempt_first_engine() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 1
    state.money = 15
    state.jokers = []
    candidate = _Voucher("Hieroglyph", price=10)
    thresholds = VoucherAcquisitionThresholds(
        minimum_money_after=0,
        minimum_persistent_value=0.0,
        minimum_purchase_advantage=0.0,
    )
    policy = VoucherAcquisitionPolicy(
        thresholds,
        item_value_estimator=_HighVoucherEstimator(),
        profiler=_NeutralProfiler(),
    )

    decision = policy.decide(state, candidate)
    passed = (
        decision.action == HOLD
        and decision.executable_action is None
        and decision.money_after == 5
        and any("early survival hold" in note for note in decision.rationale)
    )
    return SemanticCheck(
        passed,
        observed=(
            f"decision={decision.action}, money_after={decision.money_after}, "
            f"early_gate={any('early survival hold' in note for note in decision.rationale)}"
        ),
        expected="an expensive early non-structural voucher cannot spend below survival capital before the first scoring foothold",
        detail=(
            "D3's independent early-survival gate must remain authoritative even under permissive playbook thresholds "
            "or extremely large persistent-value estimates"
        ),
    )


def _hieroglyph_parent_value_fails_closed_until_downside_modeled() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 4
    state.money = 30
    candidate = _Voucher("Hieroglyph", price=10)
    shop_policy = BalatroShopPolicy()
    evaluator = VoucherParentLiteralEvaluator(shop_policy=shop_policy)

    complete, parent_value, notes = evaluator.evaluate(state, candidate)
    passed = (
        complete
        and abs(float(parent_value)) <= 1e-12
        and any("persistent hand loss" in note for note in notes)
    )
    return SemanticCheck(
        passed,
        observed=(
            f"complete={complete}, parent_value={parent_value:.3f}, "
            f"downside_note={any('persistent hand loss' in note for note in notes)}"
        ),
        expected="Hieroglyph contributes zero D14 cross-family parent value until its ante benefit and permanent hand-loss downside have a common-unit model",
        detail=(
            "D3 may still own strategic BUY/HOLD admission, but D14 must not compare the legacy fixed Hieroglyph number "
            "against literal Joker/consumable/booster utility while the persistent downside remains unresolved"
        ),
    )


RED_WHITE_PHASE4_VOUCHER_CASES = (
    SemanticBenchmarkCase(
        case_id="resource.voucher.hard_post_purchase_reserve",
        category="RESOURCE_COHERENCE",
        description="voucher value cannot buy through D3 hard liquidity floor",
        evaluate=_hard_post_purchase_reserve_blocks_voucher,
        source="Phase 4 voucher audit: D3 current-run reserve boundary",
    ),
    SemanticBenchmarkCase(
        case_id="resource.voucher.early_survival_capital",
        category="RESOURCE_COHERENCE",
        description="early expensive voucher cannot preempt first scoring engine",
        evaluate=_early_expensive_voucher_cannot_preempt_first_engine,
        source="Phase 4 voucher audit: permanent value vs immediate survival capital",
    ),
    SemanticBenchmarkCase(
        case_id="resource.voucher.hieroglyph_downside_fails_closed",
        category="RESOURCE_COHERENCE",
        description="unmodeled permanent downside cannot leak fixed D14 voucher utility",
        evaluate=_hieroglyph_parent_value_fails_closed_until_downside_modeled,
        source="Phase 4 voucher audit: D3 admission vs D14 literal parent authority",
    ),
)
