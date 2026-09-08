from games.balatro.actions import END_SHOP, BalatroAction
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.state import BalatroState


def _shop_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 25
    state.ante = 1
    state.joker_slots = 5
    state.consumable_slots = 2
    state.joker_generation_pool_observed = True
    return state


def test_parent_visible_floor_bypasses_visible_action_rescoring(monkeypatch):
    policy = BuildAwareShopRerollPolicy()
    state = _shop_state()

    def fail_visible_scores(*args, **kwargs):
        raise AssertionError("D14 visible floor must bypass D11 visible rescoring")

    monkeypatch.setattr(policy, "_visible_scores", fail_visible_scores)

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
        visible_score_floor=policy.shop_policy.hold_bias + 2.0,
    )

    assert result.current_best_score == policy.shop_policy.hold_bias + 2.0


def test_standalone_reroll_without_parent_floor_still_scores_visible_actions(monkeypatch):
    policy = BuildAwareShopRerollPolicy()
    state = _shop_state()
    called = {"value": False}

    def visible_scores(state_arg, actions_arg):
        called["value"] = True
        return []

    monkeypatch.setattr(policy, "_visible_scores", visible_scores)

    policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert called["value"] is True
