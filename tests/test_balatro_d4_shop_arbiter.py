from games.balatro.actions import BUY_AND_USE_CONSUMABLE, END_SHOP, BalatroAction
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_consumable_policy import ConsumableAcquisitionPolicy, ConsumableAcquisitionThresholds
from games.balatro.shop_reroll_policy import ShopRerollRecommendation
from games.balatro.state import BalatroState
from games.balatro.tarots import Hermit, HighPriestess


class HoldRerollPolicy:
    def recommend(self, state, visible_actions, *, reroll_cost, visible_score_floor=None):
        return ShopRerollRecommendation(
            decision="HOLD",
            reroll_cost=reroll_cost,
            executable_action=None,
            current_best_score=float(visible_score_floor or 0.0),
            future_shop_ev=0.0,
            reroll_resource_cost=0.0,
            reroll_score=-1000000000.0,
        )


def test_d12_uses_d4_buy_and_use_when_consumable_slots_are_full():
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.consumable_slots = 1
    state.consumables = [HighPriestess()]

    candidate = Hermit()
    candidate.price = 0
    candidate.area_index = 1
    state.shop_consumables = [candidate]

    thresholds = ConsumableAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        minimum_buy_and_use_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_consumable_slot_penalty=0.0,
    )
    arbiter = BuildAwareShopArbiter(
        reroll_policy=HoldRerollPolicy(),
        consumable_policy=ConsumableAcquisitionPolicy(thresholds),
    )
    decision = arbiter.decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert decision.action.name == BUY_AND_USE_CONSUMABLE
    assert decision.action.target is candidate
    assert decision.source == "CONSUMABLE_BUY_AND_USE"
    assert decision.consumable is not None
    assert decision.normalized_gain > 0.0
