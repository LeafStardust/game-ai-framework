from types import SimpleNamespace

from games.balatro.bonds import evaluate_played_retrigger_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _card(rank):
    return SimpleNamespace(rank=rank, suit="Hearts", seal="")


def _state(rank):
    # Red Seals establish the retrigger Bond without themselves being in the
    # scoring set under test. This isolates Hack's exact rank condition.
    deck = [_card("2") for _ in range(52)]
    for card in deck[:4]:
        card.seal = "Red"
    return SimpleNamespace(
        jokers=[SimpleNamespace(name="Hack")],
        owned_deck=deck,
        deck=deck,
        scoring_cards=[_card(rank)],
        hands_left=3,
    )


def test_hack_realizes_on_two_through_five():
    for rank in ("2", "3", "4", "5"):
        state = _state(rank)
        dev = evaluate_played_retrigger_bond(state)
        assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_hack_does_not_realize_on_six_or_ace():
    for rank in ("6", "A"):
        state = _state(rank)
        dev = evaluate_played_retrigger_bond(state)
        assert realize_bond(dev, state).realization == BondRealization.PARTIAL
