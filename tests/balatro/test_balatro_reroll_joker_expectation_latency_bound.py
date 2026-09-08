from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.reroll_joker_expectation_policy import (
    RerollJokerExpectationEvaluator,
    _MAX_RECORDS_PER_RARITY,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


def _joker_record(index: int, rarity: str) -> dict[str, object]:
    return {
        "center": "j_joker",
        "label": f"Joker {index}",
        "ability_name": "Joker",
        "ability_set": "JOKER",
        "rarity": rarity,
    }


def _state_with_pools(pools) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = pools
    state.joker_generation_edition_rate = 1.0
    state.visible_poker_hands = tuple(state.hand_levels)
    return state


def test_large_public_pool_has_hard_no_d2_runtime_boundary(monkeypatch):
    def forbidden_d2(*args, **kwargs):
        del args, kwargs
        raise AssertionError("reroll expectation must not invoke D2 for unseen Jokers")

    monkeypatch.setattr(PlaybookJokerAcquisitionPolicy, "decide", forbidden_d2)

    evaluator = RerollJokerExpectationEvaluator(shop_policy=BalatroShopPolicy())
    pools = {
        rarity: tuple(_joker_record(index, rarity) for index in range(40))
        for rarity in ("COMMON", "UNCOMMON", "RARE")
    }

    result = evaluator.evaluate(
        _state_with_pools(pools),
        money=10,
        expected_price=5,
    )

    assert result.complete is True
    assert result.expected_gain >= 0.0
    assert result.outcome_count == 120
    assert any("never invokes D2" in note for note in result.rationale)

    calls_note = next(
        note for note in result.rationale if note.startswith("build-transition calls=")
    )
    calls = int(calls_note.split("=", 1)[1])
    assert calls <= 3 * _MAX_RECORDS_PER_RARITY


def test_large_public_pool_still_fails_closed_on_unmodeled_joker():
    evaluator = RerollJokerExpectationEvaluator(shop_policy=BalatroShopPolicy())

    unmodeled = {
        "center": "j_not_a_real_joker",
        "label": "Unmodeled Joker",
        "ability_name": "Unmodeled Joker",
        "ability_set": "JOKER",
        "rarity": "COMMON",
    }
    pools = {
        "COMMON": (unmodeled,),
        "UNCOMMON": (_joker_record(0, "UNCOMMON"),),
        "RARE": (_joker_record(0, "RARE"),),
    }

    result = evaluator.evaluate(
        _state_with_pools(pools),
        money=10,
        expected_price=5,
    )

    assert result.complete is False
    assert result.expected_gain == 0.0
    assert any("not modeled" in note for note in result.rationale)
