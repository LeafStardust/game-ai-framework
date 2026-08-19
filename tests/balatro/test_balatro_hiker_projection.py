from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.hiker import HikerJoker
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import _normalize_card
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def _state(cards, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    return state


def test_permanent_card_bonus_scores_without_hiker_still_owned():
    ace = BalatroCard("A", "Spades", permanent_bonus=10)
    state = _state([ace], [])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 26
    assert transition.distribution.maximum == 26


def test_hiker_projects_growth_without_counting_new_bonus_on_same_activation():
    ace = BalatroCard("A", "Spades", permanent_bonus=10)
    state = _state([ace], [HikerJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 26
    assert transition.state_after_scoring.hand[0].permanent_bonus == 15
    assert ace.permanent_bonus == 10


def test_hiker_retrigger_growth_affects_later_red_seal_activation():
    ace = BalatroCard(
        "A",
        "Spades",
        seal="Red",
        permanent_bonus=10,
    )
    state = _state([ace], [HikerJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # Base High Card 5 + first Ace activation 21 + second activation 26.
    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 52
    assert transition.distribution.maximum == 52
    assert transition.state_after_scoring.hand[0].permanent_bonus == 20
    assert ace.permanent_bonus == 10


def test_hiker_only_grows_cards_that_actually_score():
    cards = [
        BalatroCard("K", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("2", "Clubs"),
    ]
    state = _state(cards, [HikerJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 60
    assert [card.permanent_bonus for card in transition.state_after_scoring.hand] == [5, 5, 0]
    assert [card.permanent_bonus for card in cards] == [0, 0, 0]


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[address]


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def test_live_memory_card_normalization_exposes_hiker_permanent_bonus():
    decoder = _FakeDecoder(
        {
            100: {
                "base": _table(101),
                "ability": _table(102),
                "config": _table(103),
                "playing_card": _integer(7),
                "debuff": _boolean(False),
            },
            101: {
                "value": _string("A"),
                "suit": _string("Spades"),
            },
            102: {"perma_bonus": _integer(15)},
            103: {"center": _table(104)},
            104: {"key": _string("c_base")},
        }
    )

    card = _normalize_card(decoder, 100)

    assert card["live_id"] == 7
    assert card["permanent_bonus"] == 15


def test_translator_maps_hiker_permanent_bonus_to_playing_card():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {
                "count": 1,
                "limit": 8,
                "cards": [
                    {
                        "value": {"rank": "A", "suit": "S"},
                        "modifier": {},
                        "live_id": 7,
                        "permanent_bonus": 15,
                    }
                ],
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.hand[0].live_id == 7
    assert state.hand[0].permanent_bonus == 15
