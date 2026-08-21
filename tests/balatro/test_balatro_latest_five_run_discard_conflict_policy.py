from types import SimpleNamespace

from games.balatro.strategy import BANNED, GOLD, BalatroStrategyTracker
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship


class BurntJoker:
    pass


class GreenJoker:
    pass


class BurglarJoker:
    pass


def _tracker():
    return BalatroStrategyTracker(RUNTIME_UNIVERSAL_BALATRO_STRATEGIES)


def test_burnt_engine_bans_green_and_burglar():
    definition = _tracker().definitions["burnt_joker_engine"]

    assert definition.relationship_for(GreenJoker(), kind="JOKER") == BANNED
    assert definition.relationship_for(BurglarJoker(), kind="JOKER") == BANNED


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
        jokers=[GreenJoker(), BurglarJoker()],
        owned_deck=[],
        deck=[],
        hand_levels={},
        hand_play_counts={},
        vouchers=(),
        consumables=(),
    )

    assert conditional_joker_relationship(
        state, "no_discard_green", BurglarJoker()
    ) == GOLD
