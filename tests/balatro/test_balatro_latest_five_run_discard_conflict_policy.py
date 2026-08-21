from types import SimpleNamespace

from games.balatro.playbook.red_white.joker_policy import _discard_conflict_indices
from games.balatro.strategy import BANNED, GOLD, BalatroStrategyTracker
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship


class BurntJoker:
    pass


class GreenJoker:
    pass


class Burglar:
    pass


def _tracker():
    return BalatroStrategyTracker(UNIVERSAL_BALATRO_STRATEGIES)


def test_burnt_engine_bans_green_and_burglar():
    definition = _tracker().definitions["burnt_joker_engine"]

    assert definition.relationship_for(GreenJoker(), kind="JOKER") == BANNED
    assert definition.relationship_for(Burglar(), kind="JOKER") == BANNED


def test_green_and_burglar_no_discard_leaves_ban_burnt():
    tracker = _tracker()

    assert tracker.definitions["no_discard_green"].relationship_for(
        BurntJoker(), kind="JOKER"
    ) == BANNED
    assert tracker.definitions["no_discard_burglar"].relationship_for(
        BurntJoker(), kind="JOKER"
    ) == BANNED


def test_burglar_remains_gold_support_for_realized_green_no_discard_engine():
    state = SimpleNamespace(
        jokers=[GreenJoker(), Burglar()],
        owned_deck=[],
        deck=[],
        hand_levels={},
        hand_play_counts={},
        vouchers=(),
        consumables=(),
    )

    assert conditional_joker_relationship(
        state, "no_discard_green", Burglar()
    ) == GOLD


def test_pairwise_shop_guard_detects_burnt_against_green_and_burglar_both_directions():
    with_burnt = SimpleNamespace(jokers=[BurntJoker()])
    with_no_discard = SimpleNamespace(jokers=[GreenJoker(), Burglar()])

    assert _discard_conflict_indices(with_burnt, GreenJoker()) == (0,)
    assert _discard_conflict_indices(with_burnt, Burglar()) == (0,)
    assert _discard_conflict_indices(with_no_discard, BurntJoker()) == (0, 1)


def test_green_and_burglar_do_not_conflict_with_each_other():
    state = SimpleNamespace(jokers=[GreenJoker()])

    assert _discard_conflict_indices(state, Burglar()) == ()
