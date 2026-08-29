from types import SimpleNamespace

from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.reroll_joker_expectation_policy import RerollJokerExpectationEvaluator


def test_unseen_reroll_joker_expectation_never_invokes_d2(monkeypatch):
    def forbidden_d2(*args, **kwargs):
        del args, kwargs
        raise AssertionError("hypothetical reroll Joker expectation must not invoke D2")

    monkeypatch.setattr(PlaybookJokerAcquisitionPolicy, "decide", forbidden_d2)

    shop_policy = SimpleNamespace(
        hold_bias=0.0,
        price_weight=0.35,
        interest_weight=1.25,
        reserve_target=5,
        reserve_weight=0.45,
    )
    evaluator = RerollJokerExpectationEvaluator(shop_policy=shop_policy)
    joker = {
        "center": "j_joker",
        "label": "Joker",
        "ability_name": "Joker",
        "ability_set": "JOKER",
        "rarity": "COMMON",
    }
    state = SimpleNamespace(
        stake_name="WHITE",
        joker_generation_pool_observed=True,
        joker_generation_pools={
            "COMMON": (dict(joker),),
            "UNCOMMON": (dict(joker),),
            "RARE": (dict(joker),),
        },
        visible_poker_hands=("HIGH_CARD", "PAIR"),
    )

    result = evaluator.evaluate(state, money=10, expected_price=5)

    assert result.complete is True
    assert result.expected_gain == 0.0
    assert result.outcome_count == 3
    assert any("never invokes D2" in note for note in result.rationale)
    assert any("deferred until the item is visible" in note for note in result.rationale)
