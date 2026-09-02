import pytest

from games.balatro.bonds.evaluation import evaluate_bond_structure
from games.balatro.bonds.model import BondRank
from games.balatro.state import BalatroState


RARE_HANDS = (
    ("straight_flush", "STRAIGHT_FLUSH"),
    ("five_kind", "FIVE_OF_A_KIND"),
    ("flush_house", "FLUSH_HOUSE"),
    ("flush_five", "FLUSH_FIVE"),
)


@pytest.mark.parametrize(("bond_id", "hand"), RARE_HANDS)
def test_rare_hand_level_investment_is_structural_bond_evidence_only(
    bond_id: str,
    hand: str,
):
    state = BalatroState()
    state.owned_deck = list(state.deck)
    state.hand_levels[hand] = 7

    developments, composition = evaluate_bond_structure(state)
    development = next(dev for dev in developments if dev.bond_id == bond_id)

    # Permanent level investment is genuine structural development and may reach
    # R1 without a complete rare-hand engine. The canonical composition records the
    # Bond evidence but exposes no named strategy/commitment authority from it.
    assert development.rank >= BondRank.R1
    assert not hasattr(composition, "strategy_candidates")
    assert not hasattr(composition, "pinned_strategy_id")
