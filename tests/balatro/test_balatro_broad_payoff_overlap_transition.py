from games.balatro.bonds.evaluation import evaluate_all_bonds
from games.balatro.bonds.model import BondRank
from games.balatro.joker_policy import _bond_transition_bonus
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.state import BalatroState


def _state(*jokers) -> BalatroState:
    state = BalatroState()
    state.owned_deck = list(state.deck)
    state.jokers = list(jokers)
    return state


def _bond(state: BalatroState, bond_id: str):
    return next(dev for dev in evaluate_all_bonds(state) if dev.bond_id == bond_id)


def test_midas_does_not_awaken_enhanced_cards_axis_without_existing_enhancements():
    state = _state()

    before_enhanced = _bond(state, "enhanced_cards")
    assert before_enhanced.rank == BondRank.LOCKED

    projected = _state(MidasMaskJoker())
    gold = _bond(projected, "gold_cards")
    enhanced = _bond(projected, "enhanced_cards")

    assert gold.rank >= BondRank.R1
    assert enhanced.rank == BondRank.LOCKED

    adjustment, rationale = _bond_transition_bonus(state, MidasMaskJoker())

    assert 0.0 < adjustment <= 0.5
    assert not any("enhanced_cards:" in note for note in rationale)
