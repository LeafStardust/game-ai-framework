from games.balatro.bonds.evaluation import EVALUATORS, extra_evaluators, missing_evaluators
from games.balatro.bonds.realization import FROZEN_BOND_IDS


def test_all_frozen_bonds_have_exactly_one_development_evaluator():
    assert missing_evaluators() == ()
    assert extra_evaluators() == ()
    assert len(EVALUATORS) == len(FROZEN_BOND_IDS) == 46
    assert set(EVALUATORS) == set(FROZEN_BOND_IDS)
