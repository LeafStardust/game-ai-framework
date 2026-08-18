from types import SimpleNamespace

from games.balatro.actions import BUY_BOOSTER, BUY_JOKER, BalatroAction
from games.balatro.shop_arbiter import ShopArbiterDecision
from games.balatro.strategy_booster_policy import StrategyAwarePlaybookShopArbiter


def test_strategy_shop_arbiter_resolves_admitted_joker_before_booster(monkeypatch):
    booster_decision = ShopArbiterDecision(
        action=BalatroAction(BUY_BOOSTER),
        source="BOOSTER",
        total=4.0,
        hold_baseline=0.35,
        normalized_gain=3.65,
        rationale=("booster originally won normalized utility",),
    )

    monkeypatch.setattr(
        "games.balatro.playbook_shop_policy.PlaybookBuildAwareShopArbiter.decide",
        lambda self, state, visible_actions, reroll_cost: booster_decision,
    )

    arbiter = StrategyAwarePlaybookShopArbiter(strategy_tracker=object())
    joker_child = SimpleNamespace(
        action=BalatroAction(BUY_JOKER),
        source="JOKER",
        total=2.0,
        decision=SimpleNamespace(action="BUY"),
    )
    monkeypatch.setattr(arbiter, "_best_joker_decision", lambda state: joker_child)
    arbiter.utility_scale = SimpleNamespace(
        joker_gain=lambda state, child: SimpleNamespace(gain=1.0)
    )

    decision = arbiter.decide(SimpleNamespace(), [], reroll_cost=None)

    assert decision.source == "JOKER"
    assert decision.action.name == BUY_JOKER
    assert decision.booster is None
    assert any("takes precedence" in note for note in decision.rationale)
