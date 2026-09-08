from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.baseball_card import BaseballCardJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.runtime.live_memory_observer import _normalize_item
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


class _JokerRarityDecoder:
    def __init__(self):
        self.tables = {
            1: {
                "ability": LuaValue("table", 2, 0),
                "config": LuaValue("table", 3, 0),
                "sort_id": LuaValue("integer", 17, 0),
            },
            2: {
                "name": LuaValue("string", "Blackboard", 0),
                "set": LuaValue("string", "Joker", 0),
            },
            3: {
                "center": LuaValue("table", 4, 0),
            },
            4: {
                "key": LuaValue("string", "j_blackboard", 0),
                "name": LuaValue("string", "Blackboard", 0),
                "rarity": LuaValue("integer", 2, 0),
            },
        }

    def string_fields(self, address):
        return self.tables.get(address, {})


def _project(jokers):
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    state.deck = []
    state.jokers = list(jokers)
    return VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )


def _with_rarity(joker, rarity):
    joker.rarity = rarity
    return joker


def test_live_joker_rarity_is_observed_and_hydrated():
    item = _normalize_item(
        _JokerRarityDecoder(),
        1,
        area_index=None,
    )

    assert item["rarity"] == "UNCOMMON"

    joker = LiveJokerFactory().create(item)
    assert type(joker).__name__ == "BlackboardJoker"
    assert joker.rarity == "UNCOMMON"


def test_baseball_card_activates_at_each_uncommon_joker_position():
    uncommon_plus_mult = _with_rarity(FlatMultJoker(), "UNCOMMON")
    common_plus_mult = _with_rarity(FlatMultJoker(), "COMMON")
    baseball = BaseballCardJoker()

    transition = _project(
        [uncommon_plus_mult, common_plus_mult, baseball]
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 184
    assert transition.distribution.maximum == 184


def test_baseball_card_ignores_non_uncommon_jokers():
    rare_plus_mult = _with_rarity(FlatMultJoker(), "RARE")
    baseball = BaseballCardJoker()

    transition = _project([rare_plus_mult, baseball])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 80


def test_baseball_card_support_fails_closed_without_other_joker_rarity():
    unknown_rarity = FlatMultJoker()
    baseball = BaseballCardJoker()

    transition = _project([unknown_rarity, baseball])

    assert transition.joker_projection_complete is False
    assert "BaseballCard" in transition.unsupported_jokers
    assert transition.distribution.minimum == 80


def test_holographic_resolves_before_independent_xmult_and_baseball():
    cavendish = _with_rarity(CavendishJoker(), "UNCOMMON")
    cavendish.edition = "Holographic"
    baseball = BaseballCardJoker()

    transition = _project([cavendish, baseball])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 792
    assert transition.distribution.maximum == 792


def test_multiple_baseball_cards_each_trigger_for_one_uncommon():
    uncommon_plus_mult = _with_rarity(FlatMultJoker(), "UNCOMMON")
    first = BaseballCardJoker()
    second = BaseballCardJoker()

    transition = _project([uncommon_plus_mult, first, second])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 180
