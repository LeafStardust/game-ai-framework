from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import (
    BUY_BOOSTER,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.state import BalatroState


class _ImmediateConsumable:
    def can_use(self, context) -> bool:
        return True


class _ConsumableFactory:
    def create(self, data, *, live_id=None):
        return _ImmediateConsumable()


class _FixedItemEstimator:
    def __init__(self, value: float) -> None:
        self.value = float(value)

    def estimate(self, state, action):
        return self.value, (f"synthetic visible marginal={self.value:.3f}",)


def _unaffordable_unopened_booster_fails_closed() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 2
    target = SimpleNamespace(label="Arcana Pack", cost=4)
    action = BalatroAction(BUY_BOOSTER, target=target)
    recommendation = BuildAwareShopBoosterPolicy().recommend(state, action)
    passed = recommendation.decision == "HOLD"
    return SemanticCheck(
        passed,
        observed=(
            f"decision={recommendation.decision}, money=${state.money}, cost=${target.cost}, "
            f"family={recommendation.family}"
        ),
        expected="D8 fails closed before hidden pack EV when the unopened booster is unaffordable",
        detail=(
            "unopened booster acquisition remains a SHOP transaction: public money legality is resolved before "
            "any family-level option value can authorize opening the pack"
        ),
    )


def _opened_pack_positive_visible_marginal_beats_zero_skip() -> SemanticCheck:
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    state.money = 0
    choice = LivePackChoice(
        area_index=0,
        address=1,
        data={"ability_set": "TAROT", "label": "The Hermit", "live_id": 1},
    )
    select = BalatroAction(SELECT_PACK_CARD, target=choice)
    skip = BalatroAction(SKIP_BOOSTER)
    policy = BalatroPackPolicy(
        item_estimator=_FixedItemEstimator(0.10),
        consumable_factory=_ConsumableFactory(),
    )
    ranked = policy.rank_actions(state, [select, skip])
    skip_score = next(score.total for score in ranked if score.action.name == SKIP_BOOSTER)
    select_score = next(score.total for score in ranked if score.action.name == SELECT_PACK_CARD)
    passed = (
        abs(float(policy.skip_bias)) <= 1e-12
        and abs(float(skip_score)) <= 1e-12
        and abs(float(select_score) - 0.10) <= 1e-12
        and ranked[0].action.name == SELECT_PACK_CARD
    )
    return SemanticCheck(
        passed,
        observed=(
            f"skip_bias={policy.skip_bias:.3f}, skip={skip_score:.3f}, "
            f"visible_choice={select_score:.3f}, selected={ranked[0].action.name}, money=${state.money}"
        ),
        expected="after opening, D9 uses a zero Skip baseline and accepts a positive visible marginal without re-pricing the sunk booster purchase",
        detail=(
            "D8 already paid money/interest/reserve cost before entering *_PACK; D9 must compare only current "
            "visible pack choices against doing nothing, even when post-purchase cash is zero"
        ),
    )


def _opened_pack_negative_visible_marginal_skips() -> SemanticCheck:
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    choice = LivePackChoice(
        area_index=0,
        address=1,
        data={"ability_set": "TAROT", "label": "The Hermit", "live_id": 1},
    )
    select = BalatroAction(SELECT_PACK_CARD, target=choice)
    skip = BalatroAction(SKIP_BOOSTER)
    policy = BalatroPackPolicy(
        item_estimator=_FixedItemEstimator(-0.10),
        consumable_factory=_ConsumableFactory(),
    )
    ranked = policy.rank_actions(state, [select, skip])
    skip_score = next(score.total for score in ranked if score.action.name == SKIP_BOOSTER)
    select_score = next(score.total for score in ranked if score.action.name == SELECT_PACK_CARD)
    passed = (
        abs(float(skip_score)) <= 1e-12
        and abs(float(select_score) + 0.10) <= 1e-12
        and ranked[0].action.name == SKIP_BOOSTER
    )
    return SemanticCheck(
        passed,
        observed=(
            f"skip={skip_score:.3f}, visible_choice={select_score:.3f}, "
            f"selected={ranked[0].action.name}"
        ),
        expected="D9 skips an opened-pack choice whose current visible marginal is below the zero doing-nothing baseline",
        detail=(
            "sunk acquisition cost must not force the agent to take a bad visible outcome merely because the pack "
            "has already been purchased"
        ),
    )


RED_WHITE_PHASE4_RESOURCE_CASES = (
    SemanticBenchmarkCase(
        case_id="resource.booster.unopened_unaffordable_hold",
        category="RESOURCE_COHERENCE",
        description="unopened booster obeys SHOP cash legality before option value",
        evaluate=_unaffordable_unopened_booster_fails_closed,
        source="Phase 4 resource audit: D8 unopened-pack transaction boundary",
    ),
    SemanticBenchmarkCase(
        case_id="resource.pack.opened_positive_uses_sunk_cost_baseline",
        category="RESOURCE_COHERENCE",
        description="opened pack accepts positive visible marginal against zero Skip",
        evaluate=_opened_pack_positive_visible_marginal_beats_zero_skip,
        source="Phase 4 resource audit: D8-to-D9 sunk-cost boundary",
    ),
    SemanticBenchmarkCase(
        case_id="resource.pack.opened_negative_can_skip",
        category="RESOURCE_COHERENCE",
        description="opened pack can skip a negative visible marginal",
        evaluate=_opened_pack_negative_visible_marginal_skips,
        source="Phase 4 resource audit: D9 zero doing-nothing baseline",
    ),
)
