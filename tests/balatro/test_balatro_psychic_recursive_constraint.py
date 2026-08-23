from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.state import BalatroState


def _cards(count: int):
    ranks = ["2", "3", "4", "5", "6"]
    return [BalatroCard(ranks[index], "Hearts") for index in range(count)]


def test_psychic_requires_exactly_five_cards_for_play_actions():
    state = BalatroState()
    state.boss_name = "The Psychic"
    state.jokers = []

    assert boss_play_action_is_legal(
        state,
        BalatroAction(PLAY_CARDS, cards=_cards(5)),
    )
    assert not boss_play_action_is_legal(
        state,
        BalatroAction(PLAY_CARDS, cards=_cards(4)),
    )


def test_psychic_does_not_block_discard_card_counts():
    state = BalatroState()
    state.boss_name = "The Psychic"
    state.jokers = []

    assert boss_play_action_is_legal(
        state,
        BalatroAction(DISCARD_CARDS, cards=_cards(2)),
    )
