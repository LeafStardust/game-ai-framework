import pytest

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.state import BalatroState


RARE_HANDS = (
    ("straight_flush", "STRAIGHT_FLUSH"),
    ("five_kind", "FIVE_OF_A_KIND"),
    ("flush_house", "FLUSH_HOUSE"),
    ("flush_five", "FLUSH_FIVE"),
)


def _candidate_mentions(candidate, bond_id: str) -> bool:
    return bond_id in set(getattr(candidate, "bond_ids", ()) or ())


@pytest.mark.parametrize(("bond_id", "hand"), RARE_HANDS)
def test_r1_rare_hand_level_investment_does_not_create_strategy_authority(
    bond_id: str,
    hand: str,
):
    state = BalatroState()
    state.owned_deck = list(state.deck)
    state.hand_levels[hand] = 7

    developments, composition = evaluate_bond_composition(state)
    development = next(dev for dev in developments if dev.bond_id == bond_id)

    # Permanent level investment is genuine structural development and reaches R1
    # under the current contribution economy. By itself, however, it is not proof
    # of a functioning rare-hand engine: no payoff Joker, enabler, semantic link,
    # or motif is present. It therefore must not gain construction/preservation
    # authority merely because a rare poker hand has been leveled.
    assert development.rank >= BondRank.R1
    assert not any(
        _candidate_mentions(candidate, bond_id)
        and candidate.commitment >= StrategyCommitment.FORMING
        for candidate in composition.strategy_candidates
    )
    assert composition.pinned_strategy_id is None
