from types import SimpleNamespace

import pytest

from games.balatro.bonds.evaluation import EVALUATORS
from games.balatro.bonds.model import BondRank
from games.balatro.state import BalatroState


def _named(name):
    return SimpleNamespace(name=name)


def _card(rank="2", *, enhancement=None, seal=None):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement=enhancement, seal=seal)


def _state(*, jokers=(), deck=()):
    state = BalatroState()
    state.jokers = list(jokers)
    state.owned_deck = list(deck)
    state.deck = list(deck)
    return state


@pytest.mark.parametrize(
    ("bond_id", "state"),
    (
        ("discard", _state(jokers=(_named("Burnt Joker"),))),
        ("blind_skip", _state(jokers=(_named("Diet Cola"),))),
        ("sell_value", _state(jokers=(_named("Egg"), _named("Gift Card")))),
        ("joker_sacrifice", _state(jokers=(_named("Riff-Raff"),))),
        ("card_destruction", _state()),
        ("hand_repetition", _state()),
        (
            "enhanced_cards",
            _state(
                jokers=(_named("Midas Mask"), _named("Marble Joker")),
                deck=tuple(_card(enhancement="Gold") for _ in range(24)),
            ),
        ),
        ("no_face_cards", _state(deck=tuple(_card(rank="2") for _ in range(40)))),
    ),
)
def test_support_and_history_cannot_create_hard_payoff_axes(bond_id, state):
    state.hand_levels["HIGH_CARD"] = 12
    state.discards_per_round = 8
    state.blinds_skipped = 12
    state.joker_sell_value_total = 100
    state.jokers_destroyed = 20
    state.cards_destroyed = 30
    state.hand_play_counts["PAIR"] = 40
    state.vampire_enhancements_consumed = 30
    state.vouchers = [_named("Telescope")]

    development = EVALUATORS[bond_id](state)

    assert not development.unlocked
    assert development.rank == BondRank.LOCKED
    assert development.contribution == 0.0


def test_each_hard_payoff_unlocks_its_own_axis():
    fixtures = {
        "discard": _state(jokers=(_named("Castle"),)),
        "blind_skip": _state(jokers=(_named("Throwback"),)),
        "sell_value": _state(jokers=(_named("Swashbuckler"),)),
        "joker_sacrifice": _state(jokers=(_named("Ceremonial Dagger"),)),
        "card_destruction": _state(jokers=(_named("Trading Card"),)),
        "hand_repetition": _state(jokers=(_named("Card Sharp"),)),
        "enhanced_cards": _state(jokers=(_named("Driver's License"),)),
        "no_face_cards": _state(jokers=(_named("Ride the Bus"),)),
    }

    for bond_id, state in fixtures.items():
        development = EVALUATORS[bond_id](state)
        assert development.unlocked, bond_id
        assert development.rank >= BondRank.R1, bond_id


def test_hand_leveling_can_exist_without_burnt_joker():
    state = _state(
        jokers=(_named("Space Joker"),),
        deck=tuple(_card(seal="Blue") for _ in range(4)),
    )
    development = EVALUATORS["hand_leveling"](state)
    assert development.unlocked
    assert development.contribution > 0.0


def test_enhancement_consumption_can_have_preconsumer_feed_evidence():
    state = _state(
        jokers=(_named("Midas Mask"), _named("Cartomancer")),
        deck=tuple(_card(enhancement="Gold") for _ in range(12)),
    )
    development = EVALUATORS["enhancement_consumption"](state)
    assert development.unlocked
    assert development.contribution > 0.0
