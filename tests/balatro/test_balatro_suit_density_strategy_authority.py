from games.balatro.bonds.evaluation import evaluate_bond_structure
from games.balatro.bonds.model import BondRank
from games.balatro.state import BalatroState


def _concentrated_hearts_state() -> BalatroState:
    state = BalatroState()
    deck = list(state.deck)
    hearts = [card for card in deck if str(getattr(card, "suit", "")).lower() == "hearts"]
    non_hearts = [card for card in deck if str(getattr(card, "suit", "")).lower() != "hearts"]

    # Preserve a 52-card public deck while creating enough permanent Hearts density
    # to cross the current Hearts R1 threshold without introducing a payoff Joker.
    concentrated = (hearts + hearts[:8] + non_hearts)[:52]
    assert sum(1 for card in concentrated if str(getattr(card, "suit", "")).lower() == "hearts") == 21

    state.owned_deck = concentrated
    return state


def test_natural_suit_density_remains_r0_structural_evidence():
    state = BalatroState()
    state.owned_deck = list(state.deck)

    developments, composition = evaluate_bond_structure(state)
    hearts = next(dev for dev in developments if dev.bond_id == "hearts")

    assert hearts.rank == BondRank.R0
    assert not hasattr(composition, "strategy_candidates")
    assert not hasattr(composition, "pinned_strategy_id")


def test_r1_density_only_suit_bond_remains_structural_evidence():
    developments, composition = evaluate_bond_structure(_concentrated_hearts_state())
    hearts = next(dev for dev in developments if dev.bond_id == "hearts")

    # R1 is legitimate structural development: the permanent deck really is
    # Hearts-concentrated. It remains Bond evidence rather than becoming a named
    # strategy identity or commitment state.
    assert hearts.rank >= BondRank.R1
    assert not hasattr(composition, "strategy_candidates")
    assert not hasattr(composition, "pinned_strategy_id")
