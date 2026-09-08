from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.card_sharp import CardSharpJoker
from games.balatro.live.runtime.live_memory_observer import _normalize_hand_levels
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


class _HandHistoryDecoder:
    def __init__(self):
        self.tables = {
            1: {
                "Pair": LuaValue("table", 2, 0),
            },
            2: {
                "level": LuaValue("integer", 3, 0),
                "played": LuaValue("integer", 7, 0),
                "played_this_round": LuaValue("integer", 1, 0),
            },
        }

    def string_fields(self, address):
        return self.tables.get(address, {})


def _pair_state(*, run_plays=0, round_plays=0):
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Hearts"),
    ]
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = [CardSharpJoker()]
    state.hand_play_counts["PAIR"] = run_plays
    state.round_hand_play_counts["PAIR"] = round_plays
    return state, cards


def _project(state, cards):
    return VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )


def test_live_memory_exposes_round_local_hand_history():
    hands = _normalize_hand_levels(
        _HandHistoryDecoder(),
        LuaValue("table", 1, 0),
    )

    assert hands["Pair"] == {
        "level": 3,
        "played": 7,
        "played_this_round": 1,
    }


def test_translator_preserves_run_and_round_hand_history_separately():
    state = BalatroState()
    DefaultBalatroStateTranslator()._translate_hand_levels(
        state,
        {
            "Pair": {
                "level": 3,
                "played": 7,
                "played_this_round": 1,
            }
        },
    )

    assert state.hand_levels["PAIR"] == 3
    assert state.hand_play_counts["PAIR"] == 7
    assert state.round_hand_play_counts["PAIR"] == 1


def test_shop_translation_clears_completed_round_card_sharp_history():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "hands": {
                "Pair": {
                    "level": 3,
                    "played": 7,
                    "played_this_round": 2,
                }
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.hand_play_counts["PAIR"] == 7
    assert state.round_hand_play_counts["PAIR"] == 0


def test_card_sharp_ignores_run_wide_history_without_round_prior_play():
    state, cards = _pair_state(run_plays=9, round_plays=0)

    transition = _project(state, cards)

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 60
    assert transition.distribution.maximum == 60


def test_card_sharp_activates_after_same_hand_was_played_this_round():
    state, cards = _pair_state(run_plays=9, round_plays=1)

    transition = _project(state, cards)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 180
    assert transition.distribution.maximum == 180


def test_card_sharp_projection_increments_both_histories_without_mutating_live_state():
    state, cards = _pair_state()

    transition = _project(state, cards)

    assert transition.state_after_scoring.hand_play_counts["PAIR"] == 1
    assert transition.state_after_scoring.round_hand_play_counts["PAIR"] == 1
    assert state.hand_play_counts["PAIR"] == 0
    assert state.round_hand_play_counts["PAIR"] == 0


def test_second_projected_pair_activates_card_sharp():
    state, cards = _pair_state()

    first = _project(state, cards)
    second = _project(first.state_after_scoring, cards)

    assert first.distribution.minimum == 60
    assert second.distribution.minimum == 180
    assert second.state_after_scoring.hand_play_counts["PAIR"] == 2
    assert second.state_after_scoring.round_hand_play_counts["PAIR"] == 2


def test_other_round_hand_history_does_not_activate_card_sharp():
    state, cards = _pair_state()
    state.round_hand_play_counts["FLUSH"] = 2

    transition = _project(state, cards)

    assert transition.distribution.minimum == 60
