from games.balatro.build.effects import (
    HELD_EFFECT,
    HELD_RETRIGGER,
    SCORE_XMULT,
    enhancement_feature,
    hand_feature,
    rank_feature,
)
from games.balatro.build.profile import BalatroBuildProfiler
from games.balatro.card import BalatroCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.state import BalatroState
from games.balatro.tarots import Chariot


def _build_state():
    state = BalatroState()
    state.money = 18
    state.ante = 3
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades"),
        BalatroCard("A", "Hearts"),
        BalatroCard("2", "Clubs"),
    ]
    state.jokers = [BaronJoker(), MimeJoker()]
    state.consumables = [Chariot()]
    state.hand_levels["PAIR"] = 3
    return state


def test_build_profile_counts_public_deck_and_slots():
    profile = BalatroBuildProfiler().profile(_build_state())

    assert profile.money == 18
    assert profile.ante == 3
    assert profile.deck_size == 4
    assert dict(profile.rank_counts)["K"] == 2
    assert dict(profile.suit_counts)["Hearts"] == 2
    assert dict(profile.enhancement_counts)["Steel"] == 1
    assert profile.free_joker_slots == 3
    assert profile.free_consumable_slots == 1
    assert profile.strength(rank_feature("K")) == 2.0
    assert profile.strength(enhancement_feature("Steel")) == 1.0
    assert profile.strength(HELD_EFFECT) == 1.0
    assert profile.strength(hand_feature("PAIR")) == 3.0


def test_build_profile_uses_owned_joker_behavior_and_consumable_capabilities():
    profile = BalatroBuildProfiler().profile(_build_state())

    assert "BaronJoker" in profile.joker_names
    assert "MimeJoker" in profile.joker_names
    assert "The Chariot" in profile.consumable_names
    assert profile.supports(SCORE_XMULT)
    assert profile.supports(HELD_RETRIGGER)
    assert profile.amplifies(HELD_EFFECT)
    assert profile.can_produce(enhancement_feature("Steel"))
    # The held Chariot can create another Steel card, but it has not been used yet.
    assert profile.strength(enhancement_feature("Steel")) == 1.0


def test_build_profile_discards_deck_order():
    state = _build_state()
    profiler = BalatroBuildProfiler()
    forward = profiler.profile(state)

    state.deck = list(reversed(state.deck))
    reversed_profile = profiler.profile(state)

    assert reversed_profile.rank_counts == forward.rank_counts
    assert reversed_profile.suit_counts == forward.suit_counts
    assert reversed_profile.enhancement_counts == forward.enhancement_counts
    assert reversed_profile.feature_strengths == forward.feature_strengths
