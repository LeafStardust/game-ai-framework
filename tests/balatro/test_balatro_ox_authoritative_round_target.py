from games.balatro.boss_trigger import matador_boss_hand_triggered
from games.balatro.hand import PokerHand
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def test_translator_preserves_authoritative_round_most_played_hand():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "round": {
                "hands_left": 4,
                "discards_left": 3,
                "most_played_poker_hand": "Pair",
            },
            "blind": {"type": "BOSS", "name": "The Ox", "score": 300},
            "hands": {},
        },
    )
    state = DefaultBalatroStateTranslator().translate(snapshot)
    assert state.round_most_played_hand == "PAIR"


def test_ox_uses_authoritative_target_even_when_counts_are_tied():
    state = BalatroState()
    state.boss_name = "The Ox"
    state.round_most_played_hand = "PAIR"
    state.hand_play_counts["PAIR"] = 2
    state.hand_play_counts["HIGH_CARD"] = 2
    state.round_hand_play_counts["PAIR"] = 0
    state.round_hand_play_counts["HIGH_CARD"] = 0

    pair = matador_boss_hand_triggered(state, PokerHand.PAIR, [])
    high_card = matador_boss_hand_triggered(state, PokerHand.HIGH_CARD, [])

    assert pair.resolvable is True
    assert pair.triggered is True
    assert high_card.resolvable is True
    assert high_card.triggered is False


def test_state_copy_preserves_authoritative_ox_target():
    state = BalatroState()
    state.round_most_played_hand = "THREE_OF_A_KIND"
    assert state.copy().round_most_played_hand == "THREE_OF_A_KIND"
