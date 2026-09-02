from types import SimpleNamespace

from games.balatro.bonds.burnt import evaluate_hand_leveling_bond
from games.balatro.bonds.gold_cards import evaluate_gold_cards_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond
from games.balatro.bonds.vampire import evaluate_enhancement_consumption_bond
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.space_joker import SpaceJoker
from games.balatro.mechanics import (
    ALL_CARDS_FACE,
    DISCARD_HAND_LEVELING,
    ENHANCEMENT_CONSUMPTION,
    ENHANCEMENT_FEED_ACCESS,
    GOLD_CARD_GENERATION,
    GOLD_CARD_SCORING_ECONOMY,
    HAND_LEVEL_COPY,
    PROBABILISTIC_HAND_LEVELING,
    component_mechanics,
)


def _component(*mechanics):
    return SimpleNamespace(name="arbitrary-component-name", mechanics=frozenset(mechanics))


def _card(rank="7", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement=enhancement, seal=seal)


def _state(*, jokers=(), deck=(), hand=(), hand_levels=None):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=list(deck),
        deck=list(deck),
        hand=list(hand),
        current_hand=list(hand),
        cards_in_hand=list(hand),
        hand_levels=dict(hand_levels or {}),
        hand_play_counts={},
        vampire_enhancements_consumed=0,
    )


def test_modeled_jokers_expose_native_mechanics():
    assert DISCARD_HAND_LEVELING in component_mechanics(BurntJoker())
    assert PROBABILISTIC_HAND_LEVELING in component_mechanics(SpaceJoker())
    assert GOLD_CARD_GENERATION in component_mechanics(MidasMaskJoker())


def test_hand_leveling_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(
            _component(DISCARD_HAND_LEVELING),
            _component(HAND_LEVEL_COPY),
        ),
    )

    dev = evaluate_hand_leveling_bond(state)

    assert dev.bond_id == "hand_leveling"
    assert dev.contribution == 13.0


def test_gold_cards_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(
            _component(GOLD_CARD_GENERATION),
            _component(GOLD_CARD_SCORING_ECONOMY),
        ),
    )

    dev = evaluate_gold_cards_bond(state)

    assert dev.bond_id == "gold_cards"
    assert dev.contribution == 10.0


def test_enhancement_consumption_uses_mechanics_not_component_display_names():
    enhanced = _card(enhancement="Bonus")
    state = _state(
        jokers=(
            _component(ENHANCEMENT_CONSUMPTION),
            _component(ENHANCEMENT_FEED_ACCESS),
            _component(ALL_CARDS_FACE),
        ),
        deck=(enhanced,),
        hand=(enhanced,),
    )

    dev = evaluate_enhancement_consumption_bond(state)
    realized = realize_bond(dev, state)

    assert dev.bond_id == "enhancement_consumption"
    assert dev.contribution == 13.0
    assert realized.realization == BondRealization.ACTIVE
