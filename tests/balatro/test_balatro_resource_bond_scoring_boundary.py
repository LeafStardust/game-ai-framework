from games.balatro.bonds.evaluation import evaluate_all_bonds
from games.balatro.bonds.model import BondRank
from games.balatro.build import JokerBuildValueEvaluator
from games.balatro.jokers.astronomer import AstronomerJoker
from games.balatro.jokers.cartomancer import CartomancerJoker
from games.balatro.state import BalatroState


def _state_with(joker):
    state = BalatroState()
    state.jokers = [joker]
    state.owned_deck = list(state.deck)
    return state


def test_tarot_resource_bond_is_structural_not_direct_scoring_power():
    joker = CartomancerJoker()
    developments = evaluate_all_bonds(_state_with(joker))
    tarot = next(dev for dev in developments if dev.bond_id == "tarot")

    assert tarot.rank >= BondRank.R1

    baseline = BalatroState()
    baseline.owned_deck = list(baseline.deck)
    value = JokerBuildValueEvaluator().evaluate(baseline, joker)

    assert value.direct_scoring_gain == 0.0
    assert value.direct_scoring_value == 0.0


def test_planet_resource_bond_is_structural_not_direct_scoring_power():
    joker = AstronomerJoker()
    developments = evaluate_all_bonds(_state_with(joker))
    planet = next(dev for dev in developments if dev.bond_id == "planet")

    assert planet.rank >= BondRank.R1

    baseline = BalatroState()
    baseline.owned_deck = list(baseline.deck)
    value = JokerBuildValueEvaluator().evaluate(baseline, joker)

    assert value.direct_scoring_gain == 0.0
    assert value.direct_scoring_value == 0.0
