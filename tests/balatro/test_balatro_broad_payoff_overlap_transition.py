from games.balatro.bonds.evaluation import evaluate_all_bonds
from games.balatro.bonds.model import BondRank
from games.balatro.joker_policy import _bond_transition_bonus
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.state import BalatroState


def _state(*jokers) -> BalatroState:
    state = BalatroState()
    state.owned_deck = list(state.deck)
    state.jokers = list(jokers)
    return state


def _bond(state: BalatroState, bond_id: str):
    return next(dev for dev in evaluate_all_bonds(state) if dev.bond_id == bond_id)


def test_midas_does_not_awaken_drivers_license_bond_without_drivers_license():
    state = _state()

    before_enhanced = _bond(state, "enhanced_cards")
    assert before_enhanced.rank == BondRank.LOCKED

    projected = _state(MidasMaskJoker())
    gold = _bond(projected, "gold_economy")
    enhanced = _bond(projected, "enhanced_cards")

    assert gold.rank >= BondRank.R1
    assert enhanced.rank == BondRank.LOCKED

    adjustment, rationale = _bond_transition_bonus(state, MidasMaskJoker())

    # Midas may receive bounded first-axis scouting value for the real Gold engine,
    # but its generic enhancement-feed role must not fabricate a second Driver's
    # License axis while that defining payoff is absent.
    assert 0.0 < adjustment <= 0.5
    assert not any("enhanced_cards:" in note for note in rationale)


def test_midas_overlap_is_rewarded_when_drivers_license_axis_is_already_real():
    state = _state(DriversLicenseJoker())

    before_enhanced = _bond(state, "enhanced_cards")
    assert before_enhanced.rank >= BondRank.R1

    projected = _state(DriversLicenseJoker(), MidasMaskJoker())
    after_enhanced = _bond(projected, "enhanced_cards")
    gold = _bond(projected, "gold_economy")

    assert after_enhanced.rank > before_enhanced.rank
    assert gold.rank >= BondRank.R1

    adjustment, rationale = _bond_transition_bonus(state, MidasMaskJoker())

    # Here the overlap is mechanically real: Driver's License already makes
    # enhancement density a live payoff and Midas also opens Gold-card economy.
    # That coherent transition may therefore exceed isolated-axis scouting value.
    assert adjustment > 0.5
    assert any("enhanced_cards:" in note for note in rationale)
