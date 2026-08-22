from types import SimpleNamespace

from games.balatro.bonds import evaluate_flush_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank, suit, enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement)


def _established_flush(hand, jokers=()):
    structure = SimpleNamespace(
        jokers=list(jokers),
        hand_levels={"FLUSH": 7},
        owned_deck=list(hand),
        deck=list(hand),
    )
    return evaluate_flush_bond(structure)


def _contribution(dev, source):
    return next((part.value for part in dev.contributions if part.source == source), 0.0)


def test_wild_card_completes_plain_flush_realization():
    hand = [
        _card("2", "Hearts"),
        _card("4", "Hearts"),
        _card("6", "Hearts"),
        _card("8", "Hearts"),
        _card("10", "Clubs", "Wild"),
    ]
    state = SimpleNamespace(jokers=[], hand=hand, current_hand=hand, cards_in_hand=hand)
    dev = _established_flush(hand)
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_wild_card_counts_for_either_smeared_color():
    smeared = _joker("Smeared Joker")
    hand = [
        _card("2", "Spades"),
        _card("4", "Clubs"),
        _card("6", "Spades"),
        _card("8", "Clubs"),
        _card("10", "Hearts", "Wild"),
    ]
    state = SimpleNamespace(jokers=[smeared], hand=hand, current_hand=hand, cards_in_hand=hand)
    dev = _established_flush(hand, [smeared])
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_wild_card_counts_toward_flush_structural_density():
    deck = [_card(str((i % 9) + 2), "Hearts") for i in range(15)]
    deck.append(_card("K", "Clubs", "Wild"))
    dev = evaluate_flush_bond(SimpleNamespace(jokers=[], owned_deck=deck, deck=deck))
    assert _contribution(dev, "Dominant suit density") == 1.0


def test_smeared_density_combines_same_color_suits_and_wild():
    smeared = _joker("Smeared Joker")
    deck = [_card(str((i % 9) + 2), "Spades" if i % 2 else "Clubs") for i in range(15)]
    deck.append(_card("K", "Hearts", "Wild"))
    dev = evaluate_flush_bond(SimpleNamespace(jokers=[smeared], owned_deck=deck, deck=deck))
    assert _contribution(dev, "Dominant suit density") == 1.0


def test_stone_hidden_suit_does_not_count_toward_flush_density():
    deck = [_card(str((i % 9) + 2), "Hearts") for i in range(15)]
    deck.append(_card("K", "Hearts", "Stone"))
    dev = evaluate_flush_bond(SimpleNamespace(jokers=[], owned_deck=deck, deck=deck))
    assert _contribution(dev, "Dominant suit density") == 0.0
