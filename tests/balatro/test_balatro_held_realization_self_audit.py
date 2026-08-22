from types import SimpleNamespace

from games.balatro.bonds import evaluate_held_cards_bond, evaluate_held_retrigger_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2", suit="Hearts", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal=seal)


def test_red_seal_steel_realizes_held_retrigger_without_mime():
    held = _card(rank="K", suit="Spades", enhancement="Steel", seal="Red")
    # Realization cannot promote a structurally dormant R0 Bond. Four Red Seals
    # establish Held Retrigger at R1; the held Red-Seal Steel card then proves
    # that the established structure is mechanically live without Mime.
    deck = [held] + [_card(rank=str(rank), seal="Red") for rank in (3, 4, 5)]
    state = SimpleNamespace(jokers=[], hand=[held], current_hand=[held], cards_in_hand=[held], owned_deck=deck, deck=deck)
    dev = evaluate_held_retrigger_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_red_seal_without_held_effect_does_not_realize_held_retrigger():
    held = _card(rank="7", suit="Hearts", enhancement="", seal="Red")
    # Keep the Bond structurally established so this test isolates realization:
    # a plain held Red Seal has nothing to retrigger while held.
    deck = [held] + [_card(rank=str(rank), seal="Red") for rank in (3, 4, 5)]
    state = SimpleNamespace(jokers=[], hand=[held], current_hand=[held], cards_in_hand=[held], owned_deck=deck, deck=deck)
    dev = evaluate_held_retrigger_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.PARTIAL


def test_blackboard_allows_wild_but_stone_blocks():
    blackboard = _joker("Blackboard")
    wild = _card(rank="7", suit="Hearts", enhancement="Wild")
    stone = _card(rank="", suit="", enhancement="Stone")

    wild_state = SimpleNamespace(jokers=[blackboard], hand=[wild], current_hand=[wild], cards_in_hand=[wild], owned_deck=[wild], deck=[wild])
    wild_dev = evaluate_held_cards_bond(wild_state)
    assert realize_bond(wild_dev, wild_state).realization == BondRealization.ACTIVE

    stone_state = SimpleNamespace(jokers=[blackboard], hand=[stone], current_hand=[stone], cards_in_hand=[stone], owned_deck=[stone], deck=[stone])
    stone_dev = evaluate_held_cards_bond(stone_state)
    assert realize_bond(stone_dev, stone_state).realization == BondRealization.PARTIAL


def test_blackboard_realizes_with_empty_hand():
    state = SimpleNamespace(jokers=[_joker("Blackboard")], hand=[], current_hand=[], cards_in_hand=[], owned_deck=[], deck=[])
    dev = evaluate_held_cards_bond(state)
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE
