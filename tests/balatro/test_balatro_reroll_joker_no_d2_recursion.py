from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.reroll_joker_expectation_policy import RerollJokerExpectationEvaluator
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


def test_unseen_reroll_joker_expectation_never_invokes_d2(monkeypatch):
    def forbidden_d2(*args, **kwargs):
        del args, kwargs
        raise AssertionError("hypothetical reroll Joker expectation must not invoke D2")

    monkeypatch.setattr(PlaybookJokerAcquisitionPolicy, "decide", forbidden_d2)

    evaluator = RerollJokerExpectationEvaluator(shop_policy=BalatroShopPolicy())
    joker = {
        "center": "j_joker",
        "label": "Joker",
        "ability_name": "Joker",
        "ability_set": "JOKER",
        "rarity": "COMMON",
    }
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "COMMON": (dict(joker),),
        "UNCOMMON": (dict(joker),),
        "RARE": (dict(joker),),
    }
    state.joker_generation_edition_rate = 1.0
    state.visible_poker_hands = tuple(state.hand_levels)

    result = evaluator.evaluate(state, money=10, expected_price=5)

    assert result.complete is True
    assert result.expected_gain >= 0.0
    assert result.outcome_count == 3
    assert any("never invokes D2" in note for note in result.rationale)
    assert any("deferred until the item is visible" in note for note in result.rationale)
    assert any("build-transition calls=" in note for note in result.rationale)
