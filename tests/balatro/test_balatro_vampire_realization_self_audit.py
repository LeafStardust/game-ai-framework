from types import SimpleNamespace

from games.balatro.bonds import evaluate_vampire_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement=enhancement)


def _state(deck, hand=()):
    return SimpleNamespace(
        jokers=[_joker("Vampire"), _joker("Midas Mask")],
        owned_deck=list(deck),
        deck=list(deck),
        hand=list(hand),
        current_hand=list(hand),
        cards_in_hand=list(hand),
        scoring_cards=[],
        played_cards=[],
        current_played_cards=[],
        vampire_enhancements_consumed=0,
    )


def test_vampire_midas_is_not_live_in_face_free_deck_without_enhanced_feed():
    deck = [_card(str(rank)) for rank in range(2, 10)] * 4
    state = _state(deck)
    dev = evaluate_vampire_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.PARTIAL


def test_vampire_midas_is_live_when_face_feed_exists_in_deck():
    deck = [_card("K")] + [_card(str(rank)) for rank in range(2, 10)] * 4
    state = _state(deck)
    dev = evaluate_vampire_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_vampire_realizes_from_direct_enhanced_feed_without_midas_face():
    enhanced = _card("7", "Bonus")
    state = SimpleNamespace(
        jokers=[_joker("Vampire")],
        owned_deck=[enhanced],
        deck=[enhanced],
        hand=[enhanced],
        current_hand=[enhanced],
        cards_in_hand=[enhanced],
        scoring_cards=[enhanced],
        played_cards=[enhanced],
        current_played_cards=[enhanced],
        vampire_enhancements_consumed=0,
    )
    dev = evaluate_vampire_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE
